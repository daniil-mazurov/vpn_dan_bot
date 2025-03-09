"""Функционал для работы с БД. Тестирование"""

import asyncio
import logging
from datetime import timedelta
from re import escape

from sqlalchemy import select

from core.config import settings
from core.exceptions import BaseBotError
from db.database import execute_query, execute_redis_query, redis_engine
from db.models import TABLES_SCHEMA, Base

logger = logging.getLogger()


async def test_base():
    """Тестирует доступность баз данных.

    Функция выполняет выборку из всех моделей базы данных
    и проверяет их доступность.

    Returns:
        list: Список результатов выполнения тестов для каждой базы данных.
    """

    async def __test_base(base):
        query = select(base)
        await execute_query(query)

    test_tasks = []

    for model in TABLES_SCHEMA.values():
        if model.__bases__[0] is Base:
            test_tasks.append(__test_base(model))

    return await asyncio.gather(*test_tasks, return_exceptions=True)


async def test_redis_base():
    """Тестирует доступность Redis базы данных.

    Функция выполняет команды ping и flushdb для проверки доступности
    Redis базы данных.

    Returns:
        list: Список результатов выполнения тестов для Redis базы данных.
    """
    pipe = redis_engine.pipeline()
    pipe.ping()
    pipe.flushdb()

    return await asyncio.gather(*(execute_redis_query(pipe),), return_exceptions=True)


async def test_server_speed():
    """Измеряет скорость Wireguard сервера.

    Функция проверяет скорость входящего и исходящего трафика,
    сначала пытаясь получить данные из Redis, а затем, если данные отсутствуют,
    выполняет команду iperf3 для измерения скорости.

    Returns:
        tuple: Кортеж из двух значений - скорость входящего и исходящего трафика в битах в секунду.

    Raises:
        BaseBotError: Если произошла ошибка при измерении пропускной способности.
    """
    pipe = redis_engine.pipeline()
    pipe.get("data:speedtest:in")
    pipe.get("data:speedtest:out")
    speed_in, speed_out = await execute_redis_query(pipe)

    try:
        if speed_in and speed_out:
            return float(speed_in), float(speed_out)

        # cmd = "iperf3 -O 1 -t 5 -Jc 172.31.0.1 | jq '.end.sum_sent.bits_per_second, .end.sum_received.bits_per_second'"
        cmd = f"""echo {escape(settings.BOT_PASS.get_secret_value())} | sudo -S docker run -i --rm \
    --name wireguard \
    --network="host" \
    -e TZ='Europe/Moscow' \
    --cap-add=NET_ADMIN \
    --privileged \
    wireguard iperf3 -O 1 -t 5 -Jc 172.31.0.1 | jq '.end.sum_sent.bits_per_second, .end.sum_received.bits_per_second'"""

        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()

        logger.info(
            f"speedtest exited with {proc.returncode}",
            extra={"Server speed_in": speed_in, "Server speed_out": speed_out},
        )

        ERROR = stderr.decode(encoding="utf-8", errors="ignore")
        assert not ERROR, "Ошибка измерения пропускной способности"

        speed_in, speed_out = (
            stdout.decode(encoding="utf-8", errors="ignore").strip("\r\n").split("\n")
        )

        pipe = redis_engine.pipeline()
        pipe.set("data:speedtest:in", speed_in)
        pipe.expire("data:speedtest:in", timedelta(minutes=30))

        pipe.set("data:speedtest:out", speed_out)
        pipe.expire("data:speedtest:out", timedelta(minutes=30))
        await execute_redis_query(pipe)

        return float(speed_in), float(speed_out)

    except AssertionError:
        logger.exception(ERROR)
        raise BaseBotError
    except ValueError:
        logger.exception("Ошибка измерения пропускной способности")
        raise BaseBotError
