import logging
from datetime import datetime, timezone
from typing import Union
from uuid import uuid4

from aiogram import Bot, F, Router
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from pytils.numeral import get_plural
from requests.exceptions import ConnectionError
from yoomoney import Client, Quickpay

import kb
import text
from core import exceptions as exc
from core.config import settings
from core.metric import async_speed_metric
from db import utils
from db.models import UserData
from handlers.utils import find_user
from states import Service
from handlers.wg_service import post_user_data

logger = logging.getLogger()
router = Router()
pay_keyboard = kb.get_pay_keyboard()


@router.message(Command("sub"))
@router.callback_query(F.data == "user_payment")
@router.message(F.text == "Подписка")
@async_speed_metric
async def subscribe_manager(trigger: Union[Message, CallbackQuery], state: FSMContext):
    user_data: UserData = await find_user(trigger)
    if not user_data:
        return

    sub_status = text.get_sub_status(user_data)

    if sub_status:
        await getattr(trigger, "message", trigger).answer(
            "\n".join(
                (
                    f"Ваша подписка: <b>{sub_status}</b>",
                    f"Ваш баланс: <b>{user_data.fbalance} руб</b>",
                    f"Вам осталось <b>{get_plural(text.get_end_sub(user_data), 'день, дня, дней')}</b>",
                )
            ),
            reply_markup=kb.get_subscr_buttons(user_data),
        )


@router.callback_query(F.data == "change_rate")
@async_speed_metric
async def post_rate_list(callback: CallbackQuery):
    user_data: UserData = await find_user(callback)
    if not user_data:
        return

    await callback.message.answer(
        "Выберите тариф",
        reply_markup=kb.get_subscr_buttons(user_data, force_rates=True),
    )


@router.callback_query(F.data.startswith("rate_info_"))
@async_speed_metric
async def choose_rate(callback: CallbackQuery):
    user_data: UserData = await find_user(callback)
    rate_id = float(callback.data.split("_")[-1])

    if not user_data:
        return
    elif user_data.stage == rate_id:
        await callback.answer("У вас уже подключен этот тариф")
        return
    elif rate_id == 0.3 and not user_data.free:
        await callback.answer(
            "К сожалению вы исчерпали возможность подключения пробного периода"
        )
        return
    elif user_data.stage == 0.3:
        await callback.answer(
            "Дождитесь окончания пробного периода или пополните баланс",
            show_alert=True,
        )
        return
    elif user_data.stage > rate_id:
        tax = user_data.stage * 10
    else:
        tax = 0

    await callback.message.answer(
        text.get_rate_descr(rate_id)
        + f"\n\n‼️ <b>Комиссия при переходе на данный тариф {tax} руб</b>",
        reply_markup=kb.get_rate_button(callback.data.split("_")[-1]),
    )


@router.callback_query(F.data.startswith("accept_rate_"))
@async_speed_metric
async def change_rate(callback: CallbackQuery, bot: Bot):
    user_data: UserData = await find_user(callback)
    rate_id = float(callback.data.split("_")[-1])
    try:
        if not user_data:
            return
        elif rate_id == 0.3:
            if user_data.free:
                await utils.update_rate_user(
                    callback.from_user.id, stage=rate_id, trial=True
                )
            else:
                await callback.answer(
                    "К сожалению вы исчерпали возможность подключения пробного периода"
                )
                return
        elif user_data.stage > rate_id:
            await utils.update_rate_user(
                callback.from_user.id, stage=rate_id, tax=user_data.stage * 10
            )
        else:
            await utils.update_rate_user(callback.from_user.id, stage=rate_id)
    except exc.DatabaseError:
        await callback.answer(text=text.DB_ERROR, show_alert=True)
    else:
        await callback.answer(
            f"Изменение тарифа на {text.rates[rate_id]} успешно!", show_alert=True
        )
        await post_user_data(callback)
    finally:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)


@router.callback_query(F.data == "top_up_balance")
async def input_balance(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Выберите сумму или введите вручную."
        f"<b>\n(Актуальная комиссия провайдера {settings.transfer_fee*100-100} %</b>",
        reply_markup=pay_keyboard,
    )
    await state.set_state(Service.balance)


@router.callback_query(F.data.startswith("pay_sub_"))
@router.message(Service.balance)
@async_speed_metric
async def pay(trigger: Union[Message, CallbackQuery], bot: Bot, state: FSMContext):
    try:
        client = Client(settings.YOO_TOKEN.get_secret_value())
        transaction_label = uuid4()
        SUM = (
            float(
                getattr(
                    trigger, "text", getattr(trigger, "data", "_None").split("_")[-1]
                )
            )
            * settings.transfer_fee
        )

        quickpay = Quickpay(
            receiver=client.account_info().account,
            quickpay_form="shop",
            targets=f"Sponsor this project ({SUM} rub)",
            paymentType="SB",
            sum=SUM,
            label=transaction_label,
        )

        await utils.insert_transaction(
            dict(
                user_id=trigger.from_user.id,
                date=datetime.now(timezone.utc),
                amount=SUM,
                label=transaction_label,
                transaction_reference=quickpay.redirected_url,
            )
        )

        await getattr(trigger, "message", trigger).answer(
            "Многоразовая ссылка на пополнение счета",
            reply_markup=kb.get_pay_url(SUM, quickpay.redirected_url),
        )
        await getattr(trigger, "message", trigger).answer(
            "В случае если у вас по каким-либо причинам не прошла оплата, обратитесь в техподдержку",
            reply_markup=kb.static_support_button,
        )

    except KeyError:
        await getattr(trigger, "message", trigger).answer(
            "Истек срок давности сообщения"
        )
    except exc.DatabaseError:
        await getattr(trigger, "message", trigger).answer(
            text=text.DB_ERROR, show_alert=True
        )
    except ConnectionError:
        await getattr(trigger, "message", trigger).answer(
            text=text.YOO_ERROR, show_alert=True
        )
    except ValueError:
        await getattr(trigger, "message", trigger).answer(
            text="Сумма должна быть числом", show_alert=True
        )
    else:
        await state.clear()
        await state.set_state()
    finally:
        await bot.delete_message(
            trigger.from_user.id, getattr(trigger, "message", trigger).message_id
        )
