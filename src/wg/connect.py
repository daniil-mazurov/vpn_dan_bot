import asyncio
import logging
import logging.config

import asyncssh
from asyncssh import SSHClientConnection

from core.config import settings

logger = logging.getLogger("asyncssh")


class WgConnection:
    """Класс для управления SSH-соединением с сервером WireGuard.

    Этот класс предоставляет методы для подключения к серверу WireGuard
    с использованием SSH.
    """

    connection: SSHClientConnection

    async def connect(self):
        """Устанавливает соединение с сервером.

        Эта функция создает асинхронное соединение с сервером WireGuard
        и устанавливает интервал поддержания соединения.

        Raises:
            asyncssh.Error: Если возникла ошибка при установлении соединения.
        """
        await asyncio.wait([asyncio.create_task(self.__create_connection())])

        self.connection.set_keepalive(interval=120)

    async def __create_connection(self):
        """Создает SSH-соединение с сервером WireGuard.

        Эта функция выполняет фактическое создание SSH-соединения с использованием
        параметров, заданных в конфигурации.

        Raises:
            asyncssh.Error: Если возникла ошибка при создании соединения.
        """
        self.connection = await asyncssh.connect(
            settings.WG_HOST,
            username=settings.WG_USER,
            client_keys=settings.WG_KEY.get_secret_value(),
            known_hosts=None,
        )
