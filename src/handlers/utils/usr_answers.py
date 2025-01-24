import logging
from typing import Union

from aiogram.types import CallbackQuery, Message

import kb
import text
from core import exceptions as exc
from db import utils
from db.models import UserActivity, UserData

logger = logging.getLogger()


async def find_user(trigger: Union[Message, CallbackQuery], configs=False):
    """Ищет пользователя в базе данных и обрабатывает его статус.

    Args:
        trigger (Union[Message, CallbackQuery]): Сообщение или обратный вызов, содержащий информацию о пользователе.
        configs (bool, optional): Флаг, указывающий, нужно ли извлекать конфигурации пользователя. По умолчанию False.

    Returns:
        UserData: Данные пользователя, если они найдены и активны.
    """
    try:
        # Извлекаем данные пользователя из базы данных
        if configs:
            user_data: UserData = await utils.get_user_with_configs(
                trigger.from_user.id
            )
        else:
            user_data: UserData = await utils.get_user(trigger.from_user.id)

        if user_data is None:
            # Если данные пользователя не найдены, предлагаем регистрацию
            await getattr(trigger, "message", trigger).answer(
                "Отсутсвуют данные пользователя. Зарегистрируйтесь",
                reply_markup=kb.static_reg_button,
            )
        elif user_data.active == UserActivity.freezed:
            await trigger.answer("Аккаунт заморожен", show_alert=True)
            return None
        elif user_data.active == UserActivity.banned:
            await trigger.answer("Аккаунт забанен", show_alert=True)
            return None
        elif user_data.active == UserActivity.deleted:
            await trigger.answer("Аккаунт удален", show_alert=True)
            return None
    except exc.DatabaseError:
        # Обрабатываем ошибки базы данных
        await trigger.answer(text=text.DB_ERROR, show_alert=True)
    else:
        return user_data


async def find_config(callback: CallbackQuery):
    """Ищет конфигурацию пользователя в базе данных.

    Args:
        callback (CallbackQuery): Обратный вызов, содержащий информацию о пользователе и конфигурации.

    Returns:
        UserConfig: Конфигурация пользователя, если она найдена.
    """
    *_, cfg_id = callback.message.text.partition("| id: ")
    try:
        # Извлекаем конфигурацию пользователя из базы данных
        user_config = await utils.get_wg_config(callback.from_user.id, cfg_id)

        assert user_config
    except exc.DatabaseError:
        # Обрабатываем ошибки базы данных
        await callback.answer(text=text.DB_ERROR, show_alert=True)
    except AssertionError:
        await callback.answer(text="Конфигурация не найдена", show_alert=True)
    else:
        return user_config
