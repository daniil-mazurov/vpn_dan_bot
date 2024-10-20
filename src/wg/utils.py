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

logger = logging.getLogger("asyncssh")


class WgConfigMaker:
    peer_counter = "~/Scripts/test"

    def __init__(self) -> None:
        self.private_key: str = None
        self.public_key: str = None
        self.countpeers: int = None

    async def _create_peer(self, conn: SSHClientConnection):
        try:
            cmd = (
                "tmp_private_key=$(wg genkey)",
                "tmp_public_key=$(echo $tmp_private_key | wg pubkey)",
                "echo $tmp_private_key",
                "echo $tmp_public_key",
                f'flock {self.peer_counter} --command \'printf "%d" "$(cat {self.peer_counter})"+1 > {self.peer_counter} && cat {self.peer_counter}\'',
                f'tmp_allowed_ips="10.1.0.$(cat {self.peer_counter})/32"',
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

    async def _ban_peer(self, conn: SSHClientConnection, reverse=False):
        if reverse:
            ban = "unban"
        else:
            ban = "ban"

        try:
            cmd = (
                f"echo {escape(settings.WG_PASS.get_secret_value())} | sudo -S ~/Scripts/pywg.py -m {ban} {self.public_key} --raises",
            )
            completed_proc = await conn.run("\n" + "\n".join(cmd), check=True)
            keys = completed_proc.stdout.strip("\n").split("\n")
            print(keys)

        except (OSError, asyncssh.Error) as e:
            logger.exception(
                "Сбой при добавлении пира в конфигурацию сервера wireguard"
            )
            raise WireguardError from e

    def _create_db_wg_model(self, user_id):
        self.user_config = dict(
            user_id=user_id,
            user_private_key=self.private_key,
            address=f"10.1.0.{self.countpeers}/32",
            server_public_key=self.public_key,
        )
        return self.user_config

    @async_speed_metric
    @validate_call
    async def move_user(
        self,
        move: Literal["add", "ban", "unban"],
        user_id: int = None,
        user_pubkey: str = None,
        conn=None,
    ):
        match move:
            case "add":
                await self._create_peer(conn)
                usr_cfg = self._create_db_wg_model(user_id)
                logger.info(f"{usr_cfg['address']=}")
                return usr_cfg
            case "ban":
                self.public_key = user_pubkey
                await self._ban_peer(conn)
            case "unban":
                self.public_key = user_pubkey
                await self._ban_peer(conn, reverse=True)


async def test_100():
    wg = WgConfigMaker()
    start = time()
    async with asyncssh.connect(
        settings.WG_HOST,
        username=settings.WG_USER,
        client_keys=settings.WG_KEY.get_secret_value(),
    ) as conn:
        coros = [
            wg.move_user(user_id=6987832296, move="add", conn=conn) for _ in range(1)
        ]
        # coros = [
        #     wg.move_user(
        #         user_pubkey="mKAB5YJSTdxsKcJvyDRw95kgFJWL4I/iRFEJLvfwrhA=",
        #         move="unban",
        #         conn=conn,
        #     )
        #     for _ in range(1)
        # ]

        coros_gen = time() - start

        await asyncio.gather(*coros)

        end = time() - start - coros_gen

        print(f"{coros_gen=}  {end=}")


if __name__ == "__main__":
    logging.config.fileConfig("log.ini", disable_existing_loggers=False)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_100())
