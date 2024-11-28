"""Функционал для работы с БД. Работа с транзакциями"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import and_, desc, insert, select, update

from core.config import settings
from core.metric import async_speed_metric
from db.database import execute_query, iter_redis_keys
from db.models import Transactions, UserActivity, UserData
from db.utils.redis import CashManager

logger = logging.getLogger()


@async_speed_metric
async def get_cash_wg_transactions(user_id):
    """Получает транзакции пользователя из кеша.

    Функция ищет транзакции пользователя в Redis, используя ключи,
    соответствующие его идентификатору.

    Args:
        user_id (str): Идентификатор пользователя.

    Returns:
        list: Список транзакций пользователя.
    """
    cash = CashManager(Transactions)

    tr_keys = await iter_redis_keys(f"data:{Transactions.__tablename__}:*:{user_id}")
    async for trans_key in tr_keys:
        cash.cmd.hgetall(trans_key)

    return await cash()


@async_speed_metric
async def delete_cash_transactions(user_id):
    """Удаляет кешированные транзакции пользователя.

    Функция удаляет все кешированные транзакции пользователя из Redis.

    Args:
        user_id (str): Идентификатор пользователя.

    Returns:
        None
    """
    rkeys = await iter_redis_keys(f"data:{Transactions.__tablename__}:*:{user_id}")
    await CashManager(Transactions).delete(*[key async for key in rkeys], fullkey=True)


@async_speed_metric
async def insert_transaction(conf: dict):
    """Вставляет новую транзакцию в базу данных.

    Функция сначала удаляет кешированные транзакции пользователя,
    а затем добавляет новую транзакцию в базу данных.

    Args:
        conf (dict): Словарь, содержащий данные транзакции.

    Returns:
        None
    """
    await delete_cash_transactions(conf["user_id"])

    query = insert(Transactions).values(**conf)
    await execute_query(query)


async def confirm_success_pay(transaction: Transactions):
    """Подтверждает успешную оплату транзакции.

    Функция проверяет, существует ли предыдущая транзакция с таким же
    ярлыком, и либо создает новую транзакцию, либо обновляет существующую.

    Args:
        transaction (Transactions): Объект транзакции.

    Returns:
        Transactions: Объект транзакции, который был создан или обновлен.
    """
    query = select(Transactions).where(Transactions.label == transaction.label)
    prev_result: Transactions = (await execute_query(query)).scalars().first()

    if getattr(prev_result, "transaction_id", None):
        query = (
            insert(Transactions)
            .values(
                user_id=prev_result.user_id,
                date=transaction.date,
                amount=transaction.amount,
                label=transaction.label,
                transaction_id=transaction.transaction_id,
                sha1_hash=transaction.sha1_hash,
                sender=transaction.sender,
                withdraw_amount=transaction.withdraw_amount,
                transaction_reference=prev_result.transaction_reference,
            )
            .returning(Transactions)
        )

    else:
        query = (
            update(Transactions)
            .values(
                date=transaction.date,
                amount=transaction.amount,
                transaction_id=transaction.transaction_id,
                sha1_hash=transaction.sha1_hash,
                sender=transaction.sender,
                withdraw_amount=transaction.withdraw_amount,
            )
            .filter_by(label=transaction.label)
            .returning(Transactions)
        )

    result: Transactions = (await execute_query(query)).scalar_one_or_none()

    if result:
        await delete_cash_transactions(result.user_id)
        await CashManager(UserData).delete(result.user_id)

    return result


async def close_free_trial(user_id):
    """Закрывает бесплатный пробный период пользователя.

    Функция обновляет тариф пользователя, переводя его в состояние
    завершенного пробного периода.

    Args:
        user_id (str): Идентификатор пользователя.

    Returns:
        UserData: Объект данных пользователя, обновленный после завершения пробного периода.
    """
    query = (
        update(UserData)
        .values(stage=1)
        .where(and_(UserData.telegram_id == user_id, UserData.stage == 0.3))
        .returning(UserData)
    )

    result: UserData = (await execute_query(query)).scalar_one_or_none()
    # NOTE не удаляется из кеша потому что кеш чистится после пополнения баланса
    return result


async def get_user_transactions(user_id):
    """Получает транзакции пользователя.

    Функция сначала пытается получить транзакции из кеша,
    а если они отсутствуют, то извлекает их из базы данных.

    Args:
        user_id (str): Идентификатор пользователя.

    Returns:
        list: Список транзакций пользователя.
    """
    trans: list[Transactions] = await get_cash_wg_transactions(user_id)

    if trans:
        return sorted(trans, key=lambda x: x.date, reverse=True)

    query = (
        select(Transactions)
        .where(Transactions.user_id == user_id)
        .order_by(desc(Transactions.date))
    )

    result: list[Transactions] = (await execute_query(query)).scalars().all()

    if result:
        await CashManager(Transactions).add(
            **{f"{trans.id}:{user_id}": trans.__ustr_dict__ for trans in result}
        )

    return result


@async_speed_metric
async def raise_money():
    """Списывает деньги с активных пользователей.

    Функция выбирает всех активных пользователей и списывает
    с их баланса определенную сумму в соответствии с их стадией.

    Returns:
        None
    """
    query = select(UserData).filter_by(active=UserActivity.active)
    users: list[UserData] = (await execute_query(query)).scalars().all()

    data = [
        dict(
            user_id=user.telegram_id,
            date=datetime.now(timezone.utc),
            amount=-1 * user.stage * settings.cost,
            withdraw_amount=-1 * user.stage * settings.cost,
            label=uuid4(),
            transaction_id="Ежедневное списание",
            transaction_reference="",
        )
        for user in users
    ]

    if data:
        query = insert(Transactions).values(data)
        await execute_query(query)

        for user in users:
            await delete_cash_transactions(user.telegram_id)
            await CashManager(UserData).delete(user.telegram_id)
