import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.utils.chat_action import ChatActionMiddleware
from aiohttp import ClientSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import handlers as hand
from core.config import settings
from core.err import exception_logging
from db import models, utils  # NOTE for subserver
from db.utils.tests import test_base, test_redis_base
from scheduler.balance import balance_decrement, users_notice
from scheduler.config_freezer import check_freeze_configs, validate_configs
from scheduler.dump import regular_dump
from scheduler.notices import send_notice
from wg.utils import SSH

logger = logging.getLogger()


@exception_logging()
def create_bot():
    """Создает экземпляр бота и диспетчера.

    Эта функция инициализирует бота с заданным токеном и
    создает диспетчер с использованием RedisStorage для хранения
    состояний.

    Returns:
        tuple: Кортеж из экземпляра бота и диспетчера.
    """
    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    storage = RedisStorage.from_url(
        settings.CASHBASE_URL,
        state_ttl=timedelta(hours=settings.cash_ttl),
        data_ttl=timedelta(hours=settings.cash_ttl),
    )

    # dp = Dispatcher(storage=MemoryStorage())  # Данные бота стираются при перезапуске
    dp = Dispatcher(storage=storage)
    dp.message.middleware(ChatActionMiddleware())
    dp.include_routers(
        hand.admin.router,
        hand.ban.router,
        hand.group.router,
        hand.account.router,
        hand.user_service.router,
        hand.info.router,
        hand.wg_service.router,
        hand.payment.router,
        hand.bug.router,
    )

    return bot, dp


def create_scheduler(bot):
    """Создает планировщик для выполнения задач.

    Эта функция инициализирует планировщик для выполнения
    различных периодических задач, таких как отправка уведомлений,
    уменьшение баланса и проверка конфигураций.

    Args:
        bot (Bot): Экземпляр бота, используемый для отправки уведомлений.

    Returns:
        AsyncIOScheduler: Экземпляр планировщика.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_notice,
        # trigger="cron",
        trigger="interval",
        seconds=3,
        # hour=00,
        # minute=00,
        # second=2,
        start_date=datetime.now() + timedelta(seconds=10),
        kwargs={"bot": bot},
    )
    scheduler.add_job(
        balance_decrement,
        trigger="interval",
        seconds=3600,
        start_date=datetime.now() + timedelta(seconds=20),
    )
    scheduler.add_job(
        users_notice,
        trigger="interval",
        seconds=3600,
        start_date=datetime.now() + timedelta(seconds=30),
        kwargs={"bot": bot},
    )
    scheduler.add_job(
        check_freeze_configs,
        trigger="interval",
        seconds=60,
        start_date=datetime.now() + timedelta(seconds=15),
    )
    scheduler.add_job(
        validate_configs,
        trigger="interval",
        seconds=3600,
        start_date=datetime.now() + timedelta(seconds=15),
    )
    scheduler.add_job(
        regular_dump,
        trigger="interval",
        seconds=3600,
        start_date=datetime.now() + timedelta(seconds=60),
    )

    return scheduler


async def start_services(
    bot: Bot, dp: Dispatcher, scheduler: AsyncIOScheduler, timeout: float = None
):
    """Запускает службы бота и планировщика.

    Эта функция инициализирует и запускает подсистемы бота, а также
    запускает планировщик для выполнения задач. Она управляет
    асинхронным опросом обновлений от Telegram.

    Args:
        bot (Bot): Экземпляр бота, который будет использоваться для
            взаимодействия с Telegram API.
        dp (Dispatcher): Диспетчер, который обрабатывает обновления
            и маршрутизирует их к соответствующим обработчикам.
        scheduler (AsyncIOScheduler): Планировщик для управления
            асинхронными задачами.
        timeout (float, optional): Максимальное время ожидания в
            секундах для выполнения задач. Если None, будет ожидать
            бесконечно.

    Returns:
        set: Множество задач, которые были созданы для выполнения.

    Raises:
        RuntimeError: Если происходит ошибка при остановке опроса.
    """
    await test_subsystem()
    scheduler.start()

    tasks = await asyncio.wait(
        [
            asyncio.create_task(job)
            for job in [
                # bot.delete_webhook(drop_pending_updates=True),
                dp.start_polling(
                    bot,
                    allowed_updates=dp.resolve_used_update_types(),
                    started_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
                ),
            ]
        ],
        timeout=timeout,
    )
    try:
        await dp.stop_polling()
    except RuntimeError:
        pass
    return tasks


async def test_subsystem():
    """Тестирует подключение к подсистемам.

    Эта функция проверяет доступность баз данных и других
    подсистем, необходимых для работы бота.

    Raises:
        Exception: Если возникает ошибка при подключении к БД.
    """
    bases = await test_base()
    bases.extend(await test_redis_base())
    bases.append(await test_subserver())
    for base in bases:
        try:
            if isinstance(base, Exception):
                raise base
        except Exception:
            logger.exception("Возникло исключение при подключении к БД")
            raise


async def test_subserver():
    """Тестирует подключение к подсерверу.

    Эта функция отправляет запрос к подсерверу для проверки его
    доступности и корректности ответа.

    Raises:
        AssertionError: Если ответ от подсервера не соответствует ожиданиям.
    """
    async with ClientSession() as session:
        url = f"{settings.subserver_url}test"
        # url = "http://127.0.0.1:5000/test"
        params = {"name": "test"}

        async with session.get(url=url, params=params) as response:
            result: dict = await response.json()
            assert result.get("message") == "Hello test"


async def start_bot():
    """Запускает бота и его службы.

    Эта функция инициализирует подключение по SSH к wireguard серверу,
    создает бота, диспетчер и планировщик, а затем запускает все службы.

    Returns:
        set: Множество задач, которые были созданы для выполнения.
    """
    await SSH.connect()
    bot, dp = create_bot()
    scheduler = create_scheduler(bot)
    return await start_services(bot, dp, scheduler)
