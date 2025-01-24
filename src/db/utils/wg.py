"""Функционал для работы с БД. Работа с конфигурациями"""

import logging

from sqlalchemy import and_, delete, insert, select, update
from sqlalchemy.orm import joinedload

from core.exceptions import DatabaseError, UniquenessError
from core.metric import async_speed_metric
from db.database import execute_query, iter_redis_keys
from db.models import FreezeSteps, UserData, WgConfig
from db.utils import get_user
from db.utils.redis import CashManager

logger = logging.getLogger()


@async_speed_metric
async def get_cash_wg_configs(user_id):
    """Получает кэшированные конфигурации WireGuard для указанного пользователя.

    Args:
        user_id (int): Идентификатор пользователя.

    Returns:
        list[WgConfig]: Список конфигураций WireGuard, связанных с пользователем.
    """
    cash = CashManager(WgConfig)

    wg_keys = await iter_redis_keys(f"data:{WgConfig.__tablename__}:*:{user_id}")
    async for wg_conf_key in wg_keys:
        cash.cmd.hgetall(wg_conf_key)

    return await cash()


@async_speed_metric
async def delete_cash_configs(user_id):
    """Удаляет кэшированные конфигурации WireGuard для указанного пользователя.

    Args:
        user_id (int): Идентификатор пользователя.
    """
    rkeys = await iter_redis_keys(f"data:{WgConfig.__tablename__}:*:{user_id}")
    await CashManager(WgConfig).delete(
        *[key async for key in rkeys],
        fullkey=True,
    )


@async_speed_metric
async def get_wg_config(user_id, cfg_id: str):
    """Получает конфигурацию WireGuard по идентификатору для указанного пользователя.

    Args:
        user_id (int): Идентификатор пользователя.
        cfg_id (str): Идентификатор конфигурации.

    Returns:
        WgConfig: Конфигурация WireGuard, если найдена, иначе None.
    """
    wg_data: list[WgConfig] = await get_cash_wg_configs(user_id)
    if wg_data:
        for wg_conf in wg_data:
            if wg_conf.user_private_key[:4] == cfg_id:
                return wg_conf

    query = select(WgConfig).where(
        and_(WgConfig.user_id == user_id, WgConfig.user_private_key.contains(cfg_id))
    )

    return (await execute_query(query)).scalar_one_or_none()


@async_speed_metric
async def get_user_with_configs(user_id):
    """Получает данные пользователя вместе с его конфигурациями WireGuard.

    Args:
        user_id (int): Идентификатор пользователя.

    Returns:
        UserData: Данные пользователя, включая конфигурации WireGuard.
    """
    user_data: UserData = await get_user(user_id)
    wg_data: list[WgConfig] = await get_cash_wg_configs(user_id)
    if wg_data:
        if user_data is not None:
            user_data.configs = wg_data

        return user_data

    query = (
        select(UserData)
        .where(UserData.telegram_id == user_id)
        .options(joinedload(UserData.configs))
    )
    result: UserData = (await execute_query(query)).unique().scalar_one_or_none()
    if result:
        await CashManager(WgConfig).add(
            **{
                f"{config.name}:{user_id}": config.__ustr_dict__
                for config in result.configs
            }
        )

    return result


@async_speed_metric
async def add_wg_config(conf: dict, user_id):
    """Добавляет новую конфигурацию WireGuard для указанного пользователя.

    Args:
        conf (dict): Конфигурация WireGuard для добавления.
        user_id (int): Идентификатор пользователя.

    Returns:
        WgConfig: Добавленная конфигурация WireGuard.

    Raises:
        DatabaseError: Если конфигурацию не удалось добавить из-за ошибки базы данных.
    """
    query = insert(WgConfig).values(**conf).returning(WgConfig)
    for _ in range(10):
        try:
            result: WgConfig = (await execute_query(query)).scalar_one_or_none()
        except UniquenessError:
            result = None
            continue
        else:
            break

    await delete_cash_configs(user_id)

    if not result:
        raise DatabaseError

    return result


@async_speed_metric
async def freeze_config(configs: list[WgConfig], freeze: FreezeSteps):
    """Замораживает указанные конфигурации WireGuard.

    Args:
        configs (list[WgConfig]): Список конфигураций WireGuard для заморозки.
        freeze (FreezeSteps): Шаг заморозки.
    """
    query = (
        update(WgConfig)
        .where(WgConfig.id.in_([config.id for config in configs]))
        .values(freeze=freeze)
        .returning(WgConfig)
    )

    result: list[WgConfig] = (await execute_query(query)).scalars().all()

    updated_users = {cfg.user_id for cfg in result}
    for user_id in updated_users:
        await delete_cash_configs(user_id)


@async_speed_metric
async def get_all_wg_configs():
    """Получает все конфигурации WireGuard.

    Returns:
        list[WgConfig]: Список всех конфигураций WireGuard.
    """
    query = select(WgConfig)

    result: list[WgConfig] = (await execute_query(query, echo=False)).scalars().all()
    return result


@async_speed_metric
async def delete_unregistered_wg_configs(configs: list[WgConfig]):
    """Удаляет незарегистрированные конфигурации WireGuard.

    Returns:
        list[WgConfig]: Список всех конфигураций WireGuard.
    """
    query = delete(WgConfig).where(WgConfig.id.in_([config.id for config in configs]))

    await execute_query(query)
