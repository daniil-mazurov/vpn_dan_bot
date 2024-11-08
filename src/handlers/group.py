from aiogram import F, Router, Bot
from aiogram.filters.chat_member_updated import (
    ChatMemberUpdatedFilter,
    IS_NOT_MEMBER,
    MEMBER,
    ADMINISTRATOR,
)
from aiogram.types import ChatMemberUpdated, Message
from core.config import settings

router = Router()
router.my_chat_member.filter(F.chat.type.in_({"group", "supergroup"}))
router.message.filter(F.chat.type != "private")

chats_variants = {"group": "группу", "supergroup": "супергруппу"}


# Не удалось воспроизвести случай добавления бота как Restricted,
# поэтому примера с ним не будет


@router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> ADMINISTRATOR)
)
async def bot_added_as_admin(event: ChatMemberUpdated):
    await event.answer(
        text=f"Привет! Спасибо, что добавили меня в "
        f'{chats_variants[event.chat.type]} "{event.chat.title}" '
        f"как администратора. ID чата: {event.chat.id}"
    )


@router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> MEMBER)
)
async def bot_added_as_member(event: ChatMemberUpdated, bot: Bot):
    chat_info = await bot.get_chat(event.chat.id)
    if chat_info.permissions.can_send_messages:
        await event.answer(
            text=f"Привет! Спасибо, что добавили меня в "
            f'{chats_variants[event.chat.type]} "{event.chat.title}" '
            f"как обычного участника. ID чата: {event.chat.id}"
        )


@router.chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> MEMBER)
)
async def new_members_hi(event: ChatMemberUpdated):
    await event.answer(
        f"Добро пожаловать в чат нашего VPN сервиса, {event.new_chat_member.user.first_name}. 🫡\n\n"
        "Здесь вы можете задавать интересующие вас вопросы, "
        "общаться с другими клиентами и авторами сервиса, "
        "а также следить за актуальными новостями и обновлениями сервиса",
    )


@router.message(F.text)
async def leave_group(message: Message):
    if message.chat.id != settings.BOT_CHAT:
        await message.chat.leave()
