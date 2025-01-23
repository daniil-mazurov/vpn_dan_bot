"""События связанные с заморозкой"""

import logging

from core.err import log_cash_error
from core.exceptions import DatabaseError, WireguardError
from db.models import FreezeSteps
from db.utils import freeze_config, get_all_wg_configs
from wg.utils import WgServerTools

logger = logging.getLogger("apscheduler")
logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)


async def check_freeze_configs():
    """Проверяет и обновляет состояние заморозки конфигураций.

    Эта функция получает все конфигурации и проверяет их состояние заморозки.
    Если конфигурация находится в состоянии ожидания разморозки, она будет разморожена.
    Если конфигурация находится в состоянии ожидания заморозки, она будет заморожена.
    Логи записываются для отслеживания изменений состояний конфигураций.

    Raises:
        DatabaseError: Если произошла ошибка при взаимодействии с базой данных.
        WireguardError: Если произошла ошибка при взаимодействии с сервером Wireguard.
    """
    try:
        configs = await get_all_wg_configs()

        wait_no_cfg = [cfg for cfg in configs if cfg.freeze == FreezeSteps.wait_no]
        for config in wait_no_cfg:
            await WgServerTools().move_user(
                move="unban", user_pubkey=config.server_public_key
            )
        if wait_no_cfg:
            await freeze_config(wait_no_cfg, freeze=FreezeSteps.no)

        wait_yes_cfg = [cfg for cfg in configs if cfg.freeze == FreezeSteps.wait_yes]
        for config in wait_yes_cfg:
            await WgServerTools().move_user(
                move="ban", user_pubkey=config.server_public_key
            )
        if wait_yes_cfg:
            await freeze_config(wait_yes_cfg, freeze=FreezeSteps.yes)

    except DatabaseError as e:
        if log_cash_error(e):
            logger.exception("Ошибка связи с БД при заморозке конфигураций")
        return
    except WireguardError as e:
        if log_cash_error(e):
            logger.exception(
                "Ошибка связи с wireguard сервером при заморозке конфигураций"
            )
        return
    except Exception as e:
        if log_cash_error(e):
            logger.exception("Ошибка обновления состояния заморозки")
        return
    else:
        if wait_no_cfg:
            logger.info(
                "Разморожены конфигурации",
                extra={"configs.ids": [config.id for config in wait_no_cfg]},
            )
        if wait_yes_cfg:
            logger.info(
                "Заморожены конфигурации",
                extra={"configs.ids": [config.id for config in wait_yes_cfg]},
            )


async def validate_configs():
    """Проверяет соответствие локальных конфигураций и конфигураций на сервере.

    Эта функция получает список пиров с сервера и локальные конфигурации.
    Она проверяет, соответствуют ли адреса пиров конфигурациям в базе данных.
    Если пир заблокирован, конфигурация будет заморожена. Если пир разблокирован, конфигурация будет разморожена.

    Raises:
        DatabaseError: Если произошла ошибка при взаимодействии с базой данных.
        WireguardError: Если произошла ошибка при взаимодействии с сервером Wireguard.
        AssertionError: Если адрес полученного пира не соответствует имеющемуся в базе данных.
    """
    try:
        server_peers = await WgServerTools().get_peer_list()
        server_peers = {peer["publickey"]: peer for peer in server_peers}

        local_configs = await get_all_wg_configs()

        to_freeze = []
        to_unfreeze = []

        for config in local_configs:
            peer = server_peers.get(config.server_public_key, None)

            if peer:
                assert str(config.address) == peer["allowedips"]

                if peer["ban"] and config.freeze in (
                    FreezeSteps.no,
                    FreezeSteps.wait_yes,
                ):
                    to_freeze.append(config)

                elif not peer["ban"] and config.freeze in (
                    FreezeSteps.yes,
                    FreezeSteps.wait_no,
                ):
                    to_unfreeze.append(config)
            else:
                logger.warning(
                    f"Найдена незарегистрированная конфигурация: {config.address}"
                )

        if to_freeze:
            await freeze_config(to_freeze, freeze=FreezeSteps.yes)
        if to_unfreeze:
            await freeze_config(to_unfreeze, freeze=FreezeSteps.no)

    except DatabaseError as e:
        if log_cash_error(e):
            logger.exception("Ошибка связи с БД при заморозке конфигураций")
    except WireguardError as e:
        if log_cash_error(e):
            logger.exception(
                "Ошибка связи с wireguard сервером при заморозке конфигураций"
            )
    except AssertionError as e:
        if log_cash_error(e):
            logger.error("Адрес полученного пира не соответствует имеющемуся в БД")
    except Exception as e:
        if log_cash_error(e):
            logger.exception("Ошибка валидации состояния заморозки")
