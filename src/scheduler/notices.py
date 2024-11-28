"""Отправка уведомлений пользователям"""

import logging
import os
from random import randint

import aiofiles
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from pytils.numeral import get_plural

from core.err import log_cash_error
from core.path import PATH
from db.models import UserData
from db.utils import close_free_trial, get_admins
from db.utils.redis import CashManager

logger = logging.getLogger("apscheduler")
logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)

queue = os.path.join(PATH, "logs", "queue.log")


async def send_notice(bot: Bot):
    """Отправляет уведомления пользователям и администраторам.

    Эта функция читает уведомления из файла очереди и обрабатывает их.
    В зависимости от типа уведомления (TRANSACTION, REPORT или CODE) отправляет
    сообщения пользователю и администраторам. Также обрабатывает
    изменения статуса пробного тарифа.

    Args:
        bot (Bot): Экземпляр бота для отправки сообщений.

    Raises:
        TelegramForbiddenError: Если бот заблокирован пользователем.
        Exception: Если произошла ошибка при обработке уведомлений.

    Notes:
        Уведомления, которые не удалось отправить, остаются в очереди для
        повторной отправки.
    """
    async with aiofiles.open(queue) as file:
        notices = (await file.read()).splitlines()

    for notice in notices.copy():
        date, _type, user_id, label, amount, *extra = notice.strip("\n#|").split("||")
        try:
            match _type:
                case "TRANSACTION":
                    user_id = int(user_id)
                    admin_ids: list[UserData] = await get_admins()

                    await bot.send_message(
                        user_id,
                        f"<b>УСПЕШНО!</b> Ваш баланс пополнен на {get_plural(float(amount), 'рубль, рубля, рублей')}!",
                    )
                    for admin in admin_ids:
                        await bot.send_message(
                            admin.telegram_id,
                            f"Казна пополнена на {get_plural(float(amount), 'рубль, рубля, рублей')} пользователем {user_id}!",
                        )

                    user_data: UserData = await close_free_trial(user_id)
                    if user_data:
                        await bot.send_message(
                            user_id,
                            "Ваш <b>Пробный тариф</b> автоматически сменен на <b>Базовый</b>",
                        )

                    logger.info(
                        "Отправлено сообщение об успешной оплате",
                        extra={"user_id": user_id},
                    )

                case "REPORT":
                    if amount and amount != "None":
                        await bot.send_message(
                            user_id,
                            f"Вашему обращению присвоен новый статус: <b>{amount}</b>. Номер обращения: {label}",
                        )
                    else:
                        admin_ids: list[UserData] = await get_admins()

                        for admin in admin_ids:
                            await bot.send_message(
                                admin.telegram_id,
                                f"Поступило обращение от пользователя {user_id}. Номер обращения: {label}",
                            )
                case "CODE":
                    user_id = int(user_id)

                    auth_code = randint(100_000, 999_999)

                    await CashManager(UserData).add(
                        {f"authcode:{user_id}": {"code": auth_code}}
                    )

                    await bot.send_message(
                        user_id,
                        f'Ваш код для авторизации\n\n<span class="tg-spoiler">{auth_code}</span>',
                    )

                    logger.info("Отправлен код авторизации", extra={"user_id": user_id})

        except TelegramForbiddenError as e:
            if log_cash_error(e):
                logger.debug("Бот заблокирован пользователем. Уведомление отложено.")
            return
        except Exception as e:
            if log_cash_error(e):
                logger.exception("Ошибка планировщика событий")
            return
        else:
            notices.pop(notice.index(notice))

    async with aiofiles.open(queue, "w") as file:
        await file.write("\n".join(notices))
