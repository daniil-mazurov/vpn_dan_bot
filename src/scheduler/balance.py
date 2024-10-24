import logging
import os
import pickle
from datetime import datetime, timedelta, timezone

from aiogram import Bot

from core.config import decr_time, noticed_time
from core.exceptions import DatabaseError
from db.models import UserActivity
from db.utils import get_valid_users, raise_money
from kb import static_balance_button
from text import get_end_sub

logger = logging.getLogger("apscheduler")
logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)


def check_time(timefile: str):
    last_updated = datetime.today()

    if os.path.isfile(timefile) and os.path.getsize(timefile) > 0:
        with open(timefile, "rb") as file:
            prev_updated: datetime = pickle.load(file)

        diff = last_updated - prev_updated

    else:
        diff = last_updated - last_updated

    if diff > timedelta(days=1):
        return True
    return False


def increment_time(timefile: str):
    with open(timefile, "rb+") as file:
        prev_updated: datetime = pickle.load(file)
        file.seek(0)
        pickle.dump(prev_updated + timedelta(days=1), file)


async def balance_decrement():
    try:
        if check_time(decr_time):
            await raise_money()
            logger.info("Произведено ежедневное списание")

            increment_time(decr_time)
    except DatabaseError:
        logger.exception(
            "Ошибка базы данных при осуществлении декремента баланса пользователей"
        )


async def users_notice(bot: Bot):
    try:
        if check_time(noticed_time):
            users = await get_valid_users(0)

            for user in users:
                end = get_end_sub(user)

                diff = datetime.now(timezone.utc) - user.updated

                if user.active == UserActivity.inactive:
                    if (timedelta(days=1) < diff < timedelta(days=2)) or (
                        timedelta(days=3) < diff < timedelta(days=4)
                        or (timedelta(days=7) < diff < timedelta(days=8))
                    ):
                        await bot.send_message(
                            user.telegram_id,
                            "Здравствуйте, ваш аккаунт заблокирован, однако если вы пополните баланс, то снова сможете пользоваться своими конфигурациями!",
                            reply_markup=static_balance_button,
                        )

                        logger.info(
                            "Отправлено уведомление о возврате в сервис",
                            extra={"user_id": user.telegram_id, "trigger": diff},
                        )

                elif end == 0:  # TODO twice executed
                    await bot.send_message(
                        user.telegram_id,
                        "Здравствуйте, пополните баланс, иначе в скором времени вы будете заблокированы.",
                        reply_markup=static_balance_button,
                    )

                    logger.info(
                        "Отправлено уведомление о блокировке",
                        extra={"user_id": user.telegram_id, "end": end},
                    )
                elif end <= 2:
                    await bot.send_message(
                        user.telegram_id,
                        "Здравствуйте, ваши средства на балансе в скором времени закончатся."
                        "По окончании этого периода ваш аккаунт будет заблокирован системой (пока вы снова не пополните баланс 🙄)",
                        reply_markup=static_balance_button,
                    )

                    logger.info(
                        "Отправлено уведомление о скорой блокировке",
                        extra={"user_id": user.telegram_id, "end": end},
                    )

            increment_time(noticed_time)

    except DatabaseError:
        logger.exception(
            "Ошибка базы данных при осуществлении декремента баланса пользователей"
        )
