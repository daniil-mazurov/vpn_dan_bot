"""Функционал для работы с БД. Работа с пользовательскими данными"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import insert, not_, select, update

from core.config import settings
from core.metric import async_speed_metric
from db.database import execute_query
from db.models import Transactions, UserActivity, UserData
from db.utils import delete_cash_transactions
from db.utils.redis import CashManager

logger = logging.getLogger()


@async_speed_metric
async def get_user(user_id):
    """Получает данные пользователя по идентификатору.

    Функция сначала пытается получить данные пользователя из кеша.
    Если данных нет, выполняется выборка из базы данных.

    Args:
        user_id (str): Идентификатор пользователя.

    Returns:
        UserData: Объект данных пользователя или None, если пользователь не найден.
    """
    result: UserData = await CashManager(UserData).get({user_id: ...})
    if result:
        return result[0]

    query = select(UserData).where(UserData.telegram_id == user_id)
    result: UserData = (await execute_query(query)).scalar_one_or_none()

    if result:
        await CashManager(UserData).add({user_id: result.__ustr_dict__})

    return result


@async_speed_metric
async def get_all_userdata(user_id):
    """Получает все данные пользователя (конфигурации, транзакции, отчеты, уведомления) по идентификатору.

    Функция сначала пытается получить данные пользователя из кеша.
    Если данных нет, выполняется выборка из базы данных.

    Args:
        user_id (str): Идентификатор пользователя.

    Returns:
        UserData(BaseModel): Объект данных пользователя или None, если пользователь не найден.
    """
    query = select(UserData).where(UserData.telegram_id == user_id)
    user: UserData = (await execute_query(query)).scalar_one_or_none()
    if user:
        all_userdata = UserData.ValidationSchemaExtended.model_validate(
            user, from_attributes=True
        )
        return all_userdata
    return user


@async_speed_metric
async def add_user(user_id, user_name):
    """Добавляет нового пользователя в базу данных.

    Функция удаляет кешированные данные пользователя и добавляет его
    в базу данных.

    Args:
        user_id (str): Идентификатор пользователя.
        user_name (str): Имя пользователя.

    Returns:
        UserData: Объект данных пользователя, который был добавлен.
    """
    await CashManager(UserData).delete(user_id)

    user_data = dict(telegram_id=user_id, telegram_name=user_name)

    query = insert(UserData).values(user_data).returning(UserData)

    return (await execute_query(query)).scalar_one_or_none()


@async_speed_metric
async def freeze_user(user_id):
    """Замораживает аккаунт пользователя.

    Функция обновляет статус пользователя на "заморожен" и создает
    транзакцию для списания средств.

    Args:
        user_id (str): Идентификатор пользователя.

    Returns:
        None
    """
    await clear_cash(user_id)

    query = (
        update(UserData)
        .values(active=UserActivity.freezed)
        .filter_by(telegram_id=user_id)
        .returning(UserData)
    )
    await execute_query(query)

    user: UserData = (await execute_query(query)).scalar_one_or_none()

    tax = -1 * user.stage * settings.cost

    if tax != 0:
        data = dict(
            user_id=user.telegram_id,
            date=datetime.now(timezone.utc),
            amount=tax,
            withdraw_amount=tax,
            label=uuid4(),
            transaction_id="Заморозка аккаунта",
            transaction_reference="",
        )

        query = insert(Transactions).values(data)
        await execute_query(query)

        await delete_cash_transactions(user.telegram_id)


@async_speed_metric
async def ban_user(user_id):
    """Банит пользователя.

    Функция обновляет статус пользователя на "заблокирован".

    Args:
        user_id (str): Идентификатор пользователя.

    Returns:
        None
    """
    await clear_cash(user_id)

    query = (
        update(UserData)
        .values(active=UserActivity.banned)
        .filter_by(telegram_id=user_id)
    )
    await execute_query(query)


@async_speed_metric
async def recover_user(user_id):
    """Восстанавливает аккаунт пользователя.

    Функция обновляет статус пользователя на "неактивный".

    Args:
        user_id (str): Идентификатор пользователя.

    Returns:
        UserData: Объект данных пользователя, который был восстановлен.
    """
    await clear_cash(user_id)

    query = (
        update(UserData)
        .values(active=UserActivity.inactive)
        .filter_by(telegram_id=user_id)
        .returning(UserData)
    )
    result: UserData = (await execute_query(query)).scalar_one_or_none()
    return result


@async_speed_metric
async def update_rate_user(user_id, stage, tax=0, trial=False):
    """Обновляет тариф пользователя.

    Функция обновляет стадию пользователя и создает транзакцию
    для списания комиссии.

    Args:
        user_id (str): Идентификатор пользователя.
        stage (float): Новая стадия пользователя.
        tax (float): Комиссия за смену тарифа. По умолчанию 0.
        trial (bool): Указывает, является ли это активацией пробного периода. По умолчанию False.

    Returns:
        UserData: Объект данных пользователя, который был обновлен.
    """
    await clear_cash(user_id)

    tax *= -1
    tax_descr = "Комиссия за смену тарифа"

    if trial:
        tax_descr = "Активация пробного периода"
        tax += 7

    query = (
        update(UserData)
        .values(stage=stage, free=False)
        .filter_by(telegram_id=user_id)
        .returning(UserData)
    )

    user: UserData = (await execute_query(query)).scalar_one_or_none()

    if tax != 0:
        data = dict(
            user_id=user.telegram_id,
            date=datetime.now(timezone.utc),
            amount=tax,
            withdraw_amount=tax,
            label=uuid4(),
            transaction_id=tax_descr,
            transaction_reference="",
        )

        query = insert(Transactions).values(data)
        await execute_query(query)

        await delete_cash_transactions(user.telegram_id)

    return user


@async_speed_metric
async def mute_user(user_id):
    """Включает или выключает уведомления для пользователя.

    Функция изменяет статус mute для пользователя.

    Args:
        user_id (str): Идентификатор пользователя.

    Returns:
        None
    """
    await clear_cash(user_id)

    query = (
        update(UserData).values(mute=not_(UserData.mute)).filter_by(telegram_id=user_id)
    )
    await execute_query(query)


@async_speed_metric
async def clear_cash(user_id):
    """Очищает кеш для пользователя.

    Функция удаляет все кешированные данные для указанного пользователя.

    Args:
        user_id (str): Идентификатор пользователя.

    Returns:
        None
    """
    await CashManager(None).clear(user_id)
