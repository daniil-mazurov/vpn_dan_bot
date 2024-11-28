import asyncio
import logging
import logging.config
import os
import sys
from re import escape
from time import time
from typing import Literal

import asyncssh
from asyncssh import SSHClientConnection
from pydantic import validate_call

sys.path.insert(1, os.path.join("C:\\code\\vpn_dan_bot\\src"))

from core.config import settings
from core.exceptions import WireguardError
from core.metric import async_speed_metric
from wg.connect import WgConnection

logger = logging.getLogger("asyncssh")

SSH = WgConnection()


class WgServerTools:
    """Класс для управления пирами и состоянием сервера WireGuard.

    Этот класс предоставляет методы для добавления, блокировки и разблокировки пиров,
    а также для получения информации о состоянии сервера WireGuard.
    """

    peer_counter = "~/Scripts/LastPeerAddress"

    def __init__(self) -> None:
        """Инициализирует экземпляр WgServerTools.

        Устанавливает значения для приватного и публичного ключей, а также счетчика пиров.
        """
        self.private_key: str = None
        self.public_key: str = None
        self.countpeers: int = None

    async def create_peer(self, conn: SSHClientConnection):
        """Создает нового пира на сервере WireGuard.

        Эта функция генерирует ключи для нового пира и добавляет его в конфигурацию сервера.

        Args:
            conn (SSHClientConnection): Установленное SSH-соединение с сервером.

        Raises:
            WireguardError: Если возникла ошибка при добавлении пира.
        """
        try:
            cmd = (
                "tmp_private_key=$(wg genkey)",
                "tmp_public_key=$(echo $tmp_private_key | wg pubkey)",
                "echo $tmp_private_key",
                "echo $tmp_public_key",
                # f'flock {self.peer_counter} --command \'printf "%d" "$(cat {self.peer_counter})"+1 > {self.peer_counter} && cat {self.peer_counter}\'',
                f"flock {self.peer_counter} --command '~/Scripts/IPgen.py --file={self.peer_counter} && cat {self.peer_counter}' ",
                f'tmp_allowed_ips="$(cat {self.peer_counter})/32"',
                f"echo {escape(settings.WG_PASS.get_secret_value())} | sudo -S ~/Scripts/pywg.py $tmp_public_key -ips=$tmp_allowed_ips --raises",
            )
            completed_proc = await conn.run("\n" + "\n".join(cmd), check=True)
            keys = completed_proc.stdout.strip("\n").split("\n")
            self.private_key, self.public_key, self.countpeers, *_ = keys
            logger.info(completed_proc.stderr)

        except (OSError, asyncssh.Error) as e:
            logger.exception(
                "Сбой при добавлении пира в конфигурацию сервера wireguard"
            )
            raise WireguardError from e

    async def ban_peer(self, conn: SSHClientConnection, reverse=False):
        """Блокирует или разблокирует пира на сервере WireGuard.

        Args:
            conn (SSHClientConnection): Установленное SSH-соединение с сервером.
            reverse (bool): Если True, разблокирует пира, иначе блокирует.

        Raises:
            WireguardError: Если возникла ошибка при изменении состояния пира.
        """
        if reverse:
            ban = "unban"
        else:
            ban = "ban"

        try:
            cmd = f"echo {escape(settings.WG_PASS.get_secret_value())} | sudo -S ~/Scripts/pywg.py -m {ban} {self.public_key} --raises"
            completed_proc = await conn.run(f"\n{cmd}", check=True)
            logger.info(completed_proc.stderr)

        except (OSError, asyncssh.Error) as e:
            logger.exception("Сбой при изменении пира в конфигурации сервера wireguard")
            raise WireguardError from e

    def create_db_wg_model(self, user_id):
        """Создает модель базы данных для нового пира.

        Args:
            user_id (int): Идентификатор пользователя.

        Returns:
            dict: Словарь с данными о пользователе и пире.
        """
        self.user_config = dict(
            user_id=user_id,
            user_private_key=self.private_key,
            address=f"{self.countpeers}/32",
            server_public_key=self.public_key,
        )
        return self.user_config

    async def check_connection(self):
        """Проверяет и устанавливает соединение с сервером.

        Если соединение закрыто, то повторно подключается к серверу.

        Returns:
            SSHClientConnection: Установленное SSH-соединение.

        Raises:
            WireguardError: Если не удалось установить соединение.
        """
        try:
            conn = SSH.connection
        except AttributeError:
            await SSH.connect()
            conn = SSH.connection

        if conn.is_closed():
            await SSH.connect()
            conn = SSH.connection
            try:
                assert conn is SSH.connection
                assert not conn.is_closed()
            except AssertionError as e:
                raise WireguardError from e
        return conn

    @async_speed_metric
    @validate_call
    async def move_user(
        self,
        move: Literal["add", "ban", "unban"],
        user_id: int = None,
        user_pubkey: str = None,
    ):
        """Добавляет, блокирует или разблокирует пира.

        Args:
            move (Literal["add", "ban", "unban"]): Действие для выполнения.
            user_id (int, optional): Идентификатор пользователя.
            user_pubkey (str, optional): Публичный ключ пользователя.

        Returns:
            dict: Конфигурация пользователя, если действие - добавление.

        Raises:
            WireguardError: Если возникла ошибка при выполнении действия.
        """
        conn = await self.check_connection()

        match move:
            case "add":
                await self.create_peer(conn)
                usr_cfg = self.create_db_wg_model(user_id)
                logger.info(f"{usr_cfg['address']=}")
                return usr_cfg
            case "ban":
                self.public_key = user_pubkey
                await self.ban_peer(conn)
            case "unban":
                self.public_key = user_pubkey
                await self.ban_peer(conn, reverse=True)

    async def get_peer_list(self):
        """Получает список пиров на сервере WireGuard.

        Returns:
            list: Список пиров с их конфигурациями.

        Raises:
            WireguardError: Если возникла ошибка при получении списка пиров.
        """
        conn = await self.check_connection()
        try:
            cmd = f"echo {escape(settings.WG_PASS.get_secret_value())} | sudo -S ~/Scripts/pywg.py -l --raises"
            completed_proc = await conn.run(f"\n{cmd}", check=True)
            peers = completed_proc.stdout.strip("\n").split("[Peer]")

            clean_peers = []
            for peer in peers:
                clean_peer = {
                    line[: line.find("=")].strip(" ").lower(): line[
                        line.find("=") + 1 :
                    ].strip(" ")
                    for line in peer.splitlines()
                    if "=" in line
                }

                if clean_peer:
                    if "ban" in peer.lower():
                        clean_peer["ban"] = True
                    else:
                        clean_peer["ban"] = False

                    clean_peers.append(clean_peer)

        except (OSError, asyncssh.Error) as e:
            logger.exception("Сбой при получении списка пиров wireguard")
            raise WireguardError from e
        else:
            logger.info(f"Got {len(clean_peers)} peer's")

            return clean_peers

    async def get_server_status(self):
        """Получает статус сервера WireGuard.

        Returns:
            str: Статус сервера ("active" или "inactive").

        Raises:
            WireguardError: Если возникла ошибка при получении статуса сервера.
        """
        conn = await self.check_connection()
        try:
            cmd = f"echo {escape(settings.WG_PASS.get_secret_value())} | sudo -S systemctl status wg-quick@wg1.service | grep Active:"
            completed_proc = await conn.run(f"\n{cmd}", check=True)
            _, status, *_ = completed_proc.stdout.strip("\n ").split()

        except (OSError, asyncssh.Error):
            logger.exception("Сбой при получении статуса сервера wireguard")
            logger.info("Server status: inactive")
            return "inactive"
        else:
            logger.info(f"Server status: {status}")
            return status

    async def get_server_cpu_usage(self):
        """Получает загрузку CPU сервера WireGuard.

        Returns:
            str: Процент загрузки CPU.

        Raises:
            WireguardError: Если возникла ошибка при получении загрузки CPU.
        """
        conn = await self.check_connection()
        try:
            cmd = "top -bn2 | grep '%Cpu' | tail -1 | grep -P '(....|...) id,'|awk '{print 100-$8 \"%\"}'"
            completed_proc = await conn.run(f"\n{cmd}", check=True)
            usage = completed_proc.stdout.strip("\n ")

        except (OSError, asyncssh.Error) as e:
            logger.exception("Сбой при получении загруженности сервера wireguard")
            logger.info("Server status: inactive")
            raise WireguardError from e
        else:
            logger.info(f"Server cpu usage: {usage}")
            return usage


async def test_100():
    """Тестирует производительность методов WgServerTools.

    Выполняет несколько асинхронных вызовов для проверки производительности
    методов получения загрузки CPU сервера.

    Raises:
        Exception: Если возникает ошибка при выполнении теста.
    """
    wg = WgServerTools()
    start = time()

    await SSH.connect()
    coros = [wg.get_server_cpu_usage() for _ in range(1)]
    coros_gen = time() - start

    await asyncio.gather(*coros)

    end = time() - start - coros_gen

    print(f"{coros_gen=}  {end=}")


if __name__ == "__main__":
    logging.config.fileConfig("log.ini", disable_existing_loggers=False)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_100())
