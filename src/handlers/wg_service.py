"""Действия с конфигурациями WireGuard"""

import logging
import os
from contextlib import suppress
from typing import Union

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.command import Command
from aiogram.types import CallbackQuery, FSInputFile, Message
from pytils.numeral import get_plural

import text
from core import exceptions as exc
from core.config import settings
from core.err import bot_except
from core.metric import async_speed_metric
from db import utils
from db.models import FreezeSteps, UserActivity, UserData, WgConfig
from handlers.utils import find_config, find_user
from kb import get_config_keyboard, remove_config, static_pay_button, why_freezed_button
from wg.utils import WgServerTools

logger = logging.getLogger()
router = Router()
router.message.filter(F.chat.type == "private")


@router.message(Command("me"))
@router.message(Command("config"))
@router.message(F.text.lower().in_(text.me))
@router.callback_query(F.data == "user_configurations")
@async_speed_metric
@bot_except
async def post_user_data(trigger: Union[Message, CallbackQuery]):
    """Отправляет данные о конфигурациях пользователя.

    Args:
        trigger (Union[Message, CallbackQuery]): Сообщение или событие обратного вызова, инициировавшее команду.

    Если у пользователя есть конфигурации, отправляет их список. Если конфигурации заморожены, отправляет сообщение об этом.
    Также информирует пользователя о максимальном количестве конфигураций для его тарифа.
    """
    user_data: UserData = await find_user(trigger, configs=True)
    if not user_data:
        return
    else:
        create_cfg_btn, create_output_cfg_btn = get_config_keyboard()

        if user_data.configs:
            await getattr(trigger, "message", trigger).answer("Ваши конфигурации:")

            user_data.configs.sort(key=lambda conf: conf.id)
            for i, config in enumerate(user_data.configs, 1):
                if config.user_private_key:
                    config_text = f"({i}/{settings.acceptable_config[user_data.stage]}) - Name: {config.name} | id: {config.user_private_key[:4]}"

                    if config.freeze != FreezeSteps.no:
                        config_text = f'🥶<b>FREEZED</b>❄️\n<span class="tg-spoiler">{config_text}</span>'

                        await getattr(trigger, "message", trigger).answer(
                            config_text, reply_markup=why_freezed_button
                        )
                    else:
                        await getattr(trigger, "message", trigger).answer(
                            config_text, reply_markup=create_output_cfg_btn
                        )

        if user_data.active == UserActivity.active:
            cfg_number = settings.acceptable_config[user_data.stage] - len(
                user_data.configs
            )

            if cfg_number <= 0:
                await getattr(trigger, "message", trigger).answer(
                    "Достигнуто максимальное количество конфигураций для данного тарифа.",
                    reply_markup=static_pay_button,
                )
            else:
                await getattr(trigger, "message", trigger).answer(
                    f"Вы можете создать еще {get_plural(cfg_number, 'конфигурацию, конфигурации, конфигураций')}",
                    reply_markup=create_cfg_btn,
                )
        elif user_data.active == UserActivity.inactive:
            await getattr(trigger, "message", trigger).answer(
                text.UNPAY, reply_markup=static_pay_button
            )


@router.message(Command("create"))
@router.callback_query(F.data == "create_configuration")
@async_speed_metric
@bot_except
async def create_config_data(trigger: Union[Message, CallbackQuery], bot: Bot):
    """Создает новую конфигурацию для пользователя.

    Args:
        trigger (Union[Message, CallbackQuery]): Сообщение или событие обратного вызова, инициировавшее команду.
        bot (Bot): Экземпляр бота для выполнения действий.

    Проверяет, может ли пользователь создать новую конфигурацию, и создает ее, если это возможно.
    В случае ошибок отправляет соответствующие сообщения.
    """
    try:
        user_data: UserData = await find_user(trigger, configs=True)
        if not user_data:
            return
        elif user_data.active != UserActivity.active:
            raise exc.PayError

        elif len(user_data.configs) < settings.acceptable_config[user_data.stage]:
            wg = WgServerTools()
            conf = await wg.move_user(move="add", user_id=trigger.from_user.id)
            config: WgConfig = await utils.add_wg_config(
                conf, user_id=trigger.from_user.id
            )

        else:
            raise exc.StagePayError

    except exc.DatabaseError:
        await trigger.answer(text=text.DB_ERROR, show_alert=True)
    except exc.WireguardError:
        await trigger.answer(text=text.WG_ERROR, show_alert=True)
    except exc.StagePayError:
        await getattr(trigger, "message", trigger).answer(
            "Достигнуто максимальное количество конфигураций для данного тарифа.",
            reply_markup=static_pay_button,
        )
        await bot.delete_message(
            trigger.from_user.id, getattr(trigger, "message", trigger).message_id
        )
    except exc.PayError:
        await getattr(trigger, "message", trigger).answer(
            text.UNPAY, reply_markup=static_pay_button
        )
    else:
        create_cfg_btn, create_output_cfg_btn = get_config_keyboard()

        await trigger.answer(text="Конфигурация успешно создана", show_alert=True)
        await getattr(trigger, "message", trigger).answer(
            f"Конфигурация: {config.name} | id: {config.user_private_key[:4]}",
            reply_markup=create_output_cfg_btn,
        )

        with suppress(TelegramBadRequest):
            cfg_number = get_plural(
                settings.acceptable_config[user_data.stage]
                - len(user_data.configs)
                - 1,
                "конфигурацию, конфигурации, конфигураций",
            )
            await getattr(trigger, "message", trigger).edit_text(
                f"Вы можете создать еще {cfg_number}", reply_markup=create_cfg_btn
            )

        if cfg_number.startswith("0"):
            await bot.delete_message(
                trigger.from_user.id, getattr(trigger, "message", trigger).message_id
            )


@router.callback_query(F.data == "remove_config_confirm")
@bot_except
async def remove_config_data_confirm(callback: CallbackQuery):
    """Подтверждение удаления конфигурации.

    Args:
        callback (CallbackQuery): Событие обратного вызова, инициировавшее команду.
    """

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            "После удаления конфигурации вы больше не сможете подключаться по ней к VPN-серверу. "
            "Для восстановления подключения вам необходимо будет создать новую конфигурацию и заменить ей старую в vpn-приложении"
            f"\n\n? Вы уверены, что хотите удалить конфигурацию {callback.message.text}",
            reply_markup=remove_config(),
        )


@router.callback_query(F.data == "remove_config_cancel")
@bot_except
async def remove_config_data_cancel(callback: CallbackQuery):
    """Отмена удаления конфигурации.

    Args:
        callback (CallbackQuery): Событие обратного вызова, инициировавшее команду.
    """
    _, create_output_cfg_btn = get_config_keyboard()

    *_, old_cfg_message = callback.message.text.split("удалить конфигурацию ")

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            old_cfg_message, reply_markup=create_output_cfg_btn
        )


@router.callback_query(F.data == "remove_config")
@async_speed_metric
@bot_except
async def remove_config_data(callback: CallbackQuery, bot: Bot):
    """Удаляет конфигурацию с WG сервера, а затем из БД.

    Args:
        callback (CallbackQuery): Событие обратного вызова, инициировавшее команду.
    """

    try:
        user_config: WgConfig = await find_config(callback)
        if not user_config:
            return

        wg = WgServerTools()
        await wg.move_user(move="del", server_pubkey=user_config.server_public_key)

        await utils.delete_wg_config(user_config)

    except exc.DatabaseError:
        await callback.answer(text=text.DB_ERROR, show_alert=True)
    except exc.WireguardError:
        await callback.answer(text=text.WG_ERROR, show_alert=True)
    else:
        await callback.answer(text="Конфигурация успешно удалена", show_alert=True)
    finally:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)


@router.callback_query(F.data == "create_conf_text")
@async_speed_metric
@bot_except
async def get_config_text(callback: CallbackQuery, bot: Bot):
    """Отправляет текст конфигурации пользователю.

    Args:
        callback (CallbackQuery): Событие обратного вызова, инициировавшее команду.

    Отправляет текст конфигурации, связанный с пользователем, в формате, удобном для чтения.
    """
    user_config: WgConfig = await find_config(callback)
    if not user_config:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
        return

    config = text.get_config_data(user_config)

    await callback.message.answer("Конфигурация " + callback.message.text)
    await callback.message.answer(f"<pre>{config}</pre>")


@router.callback_query(F.data == "create_conf_file")
@async_speed_metric
@bot_except
async def get_config_file(callback: CallbackQuery, bot: Bot):
    """Отправляет файл конфигурации пользователю.

    Args:
        callback (CallbackQuery): Событие обратного вызова, инициировавшее команду.

    Создает файл конфигурации и отправляет его пользователю в виде документа.
    """
    user_config: WgConfig = await find_config(callback)
    if not user_config:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
        return

    config = text.get_config_data(user_config)
    config_file = await text.create_config_file(config)

    await callback.message.answer("Конфигурация " + callback.message.text)
    await callback.message.answer_document(FSInputFile(config_file, "myVpn.conf"))
    await callback.message.answer(
        "‼️ Если у вас возникает ошибка: <b>Неправильное имя</b> "
        "Проверьте имя файла: в нем не должно быть пробелов или спецсимволов (подчеркиваний, скобок ...), "
        "длина имени файла должна быть не более 10 символов"
    )
    os.remove(config_file)


@router.callback_query(F.data == "create_conf_qr")
@async_speed_metric
@bot_except
async def get_config_qr(callback: CallbackQuery, bot: Bot):
    """Отправляет QR-код конфигурации пользователю.

    Args:
        callback (CallbackQuery): Событие обратного вызова, инициировавшее команду.

    Создает QR-код конфигурации и отправляет его пользователю в виде изображения.
    """
    user_config: WgConfig = await find_config(callback)
    if not user_config:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
        return

    config = text.get_config_data(user_config)
    config_qr = text.create_config_qr(config)

    await callback.message.answer("Конфигурация " + callback.message.text)
    await callback.message.answer_photo(
        FSInputFile(config_qr, f"{user_config.name}_wg.conf")
    )
    os.remove(config_qr)
