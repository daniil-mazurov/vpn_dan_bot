"""Функционал администратора"""

import logging

from aiogram import Bot, F, Router
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message
from aiogram.utils.formatting import Bold, as_marked_section
from pytils.numeral import get_plural

import text
from core import exceptions as exc
from core.config import settings
from core.err import bot_except
from core.metric import async_speed_metric
from db import utils
from db.models import UserData
from states import AdminService

logger = logging.getLogger()
router = Router()
router.message.filter(F.chat.type == "private")


@router.message(Command("admin"))
@async_speed_metric
@bot_except
async def admin_actions(message: Message):
    """Обрабатывает команду /admin и предоставляет список команд администратора.

    Args:
        message (Message): Сообщение от пользователя.
    """
    try:
        user_data: UserData = await utils.get_user(message.from_user.id)
        if getattr(user_data, "admin", False):
            help_t = as_marked_section(
                Bold("Функционал администратора телеграмм бота"),
                "/admin - список команд администратора",
                "/backup - выгрузить бэкап БД в виде excel таблицы",
                "/send - рассылка сообщения всем зарегистрированным пользователям",
                "/close - уведомление пользователей о технических работах на сервере",
                "/open - уведомление пользователей об окончании технических работ на сервере",
                marker="~ ",
            )

            await message.answer(**help_t.as_kwargs())

        else:
            await message.answer(text.only_admin)
    except exc.DatabaseError:
        await message.answer(text.DB_ERROR)


@router.message(F.text == settings.ADMIN_PASS.get_secret_value())
@async_speed_metric
@bot_except
async def become_an_admin(message: Message, bot: Bot):
    """Позволяет пользователю стать администратором, если введен правильный пароль.

    Args:
        message (Message): Сообщение от пользователя.
        bot (Bot): Экземпляр бота.
    """
    try:
        user_data: UserData = await utils.set_admin(message.from_user.id)
    except exc.DatabaseError:
        await message.answer(text.DB_ERROR)
    else:
        if getattr(user_data, "admin", False):
            await message.answer("Вы успешно зарегистрированы как администратор!")
        else:
            await message.answer(
                "Пароль верный! Однако для начала необходимо зарегистрироваться! Попробуйте ввести команду /reg"
            )
    finally:
        await bot.delete_message(message.from_user.id, message.message_id)


@router.message(Command("backup"))
@async_speed_metric
@bot_except
async def get_backup(message: Message):
    """Создает резервную копию базы данных и отправляет ее пользователю.

    Args:
        message (Message): Сообщение от пользователя.
    """
    try:
        user_data: UserData = await utils.get_user(message.from_user.id)
        if getattr(user_data, "admin", False):
            backup = await utils.async_backup()
            await message.answer_document(FSInputFile(backup))
        else:
            await message.answer(text.only_admin)
    except exc.BackupError as e:
        await message.answer(e.args[0])
    except exc.DatabaseError:
        await message.answer(text.DB_ERROR)


@router.message(Command("send"))
@async_speed_metric
@bot_except
async def admin_mailing_start(message: Message, state: FSMContext):
    """Запускает процесс рассылки сообщения всем зарегистрированным пользователям.

    Args:
        message (Message): Сообщение от пользователя.
        state (FSMContext): Контекст состояния для управления состоянием бота.
    """
    try:
        user_data: UserData = await utils.get_user(message.from_user.id)
        if getattr(user_data, "admin", False):
            await state.set_state(AdminService.mailing_confirm)
            await message.answer(
                "Введите сообщение для рассылки зарегистрированным пользователям"
            )
        else:
            await message.answer(text.only_admin)
    except exc.DatabaseError:
        await message.answer(text.DB_ERROR)


@router.message(AdminService.mailing_confirm, F.text)
@async_speed_metric
@bot_except
async def admin_mailing_confirm(message: Message, state: FSMContext):
    """Подтверждает сообщение для рассылки и запрашивает подтверждение статуса администратора.

    Args:
        message (Message): Сообщение от пользователя.
        state (FSMContext): Контекст состояния для управления состоянием бота.
    """
    try:
        user_data: UserData = await utils.get_user(message.from_user.id)
        if getattr(user_data, "admin", False):
            await state.set_state(AdminService.mailing_message)
            await message.answer(f"Сообщение для рассылки:\n<b>{message.text}</b>")
            await message.answer(
                "Вы уверены, что хотите отправить это <b>ВСЕМ</b> пользователям? "
                "Для отмены нажмите /cancel или введите `нет`"
            )
            await state.update_data({"mailing_message": message.text})

        else:
            await message.answer(text.only_admin)
    except exc.DatabaseError:
        await message.answer(text.DB_ERROR)


@router.message(AdminService.mailing_message, F.text.lower().in_(text.yes))
@async_speed_metric
@bot_except
async def admin_mailing_finish(message: Message, bot: Bot, state: FSMContext):
    """Завершает процесс рассылки сообщения всем пользователям.

    Args:
        message (Message): Сообщение от пользователя.
        bot (Bot): Экземпляр бота.
        state (FSMContext): Контекст состояния для управления состоянием бота.
    """
    try:
        user_data: UserData = await utils.get_user(message.from_user.id)
        if getattr(user_data, "admin", False):
            mailing_message = (await state.get_data())["mailing_message"]

            all_users_data: list[UserData] = await utils.get_valid_users(
                message.from_user.id
            )

            for user_data in all_users_data:
                await bot.send_message(user_data.telegram_id, mailing_message)
            await message.answer(
                f"Сообщение отправлено {get_plural(len(all_users_data), 'пользователю, пользователям, пользователям')}"
            )

        else:
            await message.answer(text.only_admin)

        await state.clear()
        await state.set_state()

    except exc.DatabaseError:
        await message.answer(text.DB_ERROR)


@router.message(AdminService.mailing_message, Command("cancel"))
@router.message(AdminService.mailing_message, F.text.lower().in_(text.no))
@async_speed_metric
@bot_except
async def admin_mailing_cancel(message: Message, state: FSMContext):
    """Отменяет процесс рассылки сообщения.

    Args:
        message (Message): Сообщение от пользователя.
        state (FSMContext): Контекст состояния для управления состоянием бота.
    """
    await message.answer("Отменено")

    await state.clear()
    await state.set_state()


@router.message(AdminService.mailing_message, F.text)
@async_speed_metric
@bot_except
async def admin_mailing_repeat(message: Message):
    """Запрашивает повторное подтверждение от администратора.

    Args:
        message (Message): Сообщение от пользователя.
    """
    await message.answer("<b>ДА ИЛИ НЕТ?!</b>")


@router.message(Command("close"))
@bot_except
async def admin_mailing_stop_server(message: Message, bot: Bot):
    """Уведомляет пользователей о технических работах на сервере.

    Args:
        message (Message): Сообщение от пользователя.
        bot (Bot): Экземпляр бота.
    """
    try:
        user_data: UserData = await utils.get_user(message.from_user.id)
        if getattr(user_data, "admin", False):
            all_users_data: list[UserData] = await utils.get_valid_users(
                message.from_user.id
            )

            for user_data in all_users_data:
                await bot.send_message(user_data.telegram_id, text.SERVER_STOPPED)
            await message.answer(
                f"Сообщение отправлено {get_plural(len(all_users_data), 'пользователю, пользователям, пользователям')}"
            )

        else:
            await message.answer(text.only_admin)

    except exc.DatabaseError:
        await message.answer(text.DB_ERROR)


@router.message(Command("open"))
@bot_except
async def admin_mailing_start_server(message: Message, bot: Bot):
    """Уведомляет пользователей об окончании технических работ на сервере.

    Args:
        message (Message): Сообщение от пользователя.
        bot (Bot): Экземпляр бота.
    """
    try:
        user_data: UserData = await utils.get_user(message.from_user.id)
        if getattr(user_data, "admin", False):
            all_users_data: list[UserData] = await utils.get_valid_users(
                message.from_user.id
            )

            for user_data in all_users_data:
                await bot.send_message(user_data.telegram_id, text.SERVER_STARTED)
            await message.answer(
                f"Сообщение отправлено {get_plural(len(all_users_data), 'пользователю, пользователям, пользователям')}"
            )

        else:
            await message.answer(text.only_admin)

    except exc.DatabaseError:
        await message.answer(text.DB_ERROR)
