"""Функкционал для работы с БД. Администратор"""

import logging

from sqlalchemy import and_, not_, select, update

from core.metric import async_speed_metric
from db.database import execute_query
from db.models import UserActivity, UserData
from db.utils.redis import CashManager

logger = logging.getLogger()


@async_speed_metric
async def set_admin(user_id):
    """Устанавливает пользователя администратором.

    Удаляет кэшированные данные пользователя и обновляет его статус в базе данных.

    Args:
        user_id (int): Идентификатор пользователя, которого необходимо установить администратором.

    Returns:
        UserData | None: Объект UserData, если обновление прошло успешно, иначе None.
    """
    await CashManager(UserData).delete(user_id)

    query = (
        update(UserData)
        .values(admin=True)
        .filter_by(telegram_id=user_id)
        .returning(UserData)
    )
    return (await execute_query(query)).scalar_one_or_none()


@async_speed_metric
async def get_valid_users(my_id):
    """Получает список всех активных пользователей, кроме указанного.

    Фильтрует пользователей по различным критериям, включая статус активности и настройки.

    Args:
        my_id (int): Идентификатор пользователя, который будет исключен из списка.

    Returns:
        list[UserData]: Список объектов UserData, представляющих активных пользователей.
    """
    query = select(UserData).where(
        and_(
            not_(UserData.mute),
            UserData.telegram_id != my_id,
            UserData.active != UserActivity.freezed,
            UserData.active != UserActivity.banned,
            UserData.active != UserActivity.deleted,
            UserData.stage != 0,
        )
    )
    results: list[UserData] = (await execute_query(query)).scalars().all()
    return results


@async_speed_metric
async def get_all_users():
    """Получает список всех пользователей.

    Запрашивает все записи пользователей из базы данных.

    Returns:
        list[UserData]: Список всех объектов UserData.
    """
    query = select(UserData)
    results: list[UserData] = (await execute_query(query)).scalars().all()
    return results


@async_speed_metric
async def get_admins():
    """Получает список всех администраторов.

    Фильтрует пользователей по статусу администратора и активности.

    Returns:
        list[UserData]: Список объектов UserData, представляющих администраторов.
    """
    query = select(UserData).where(
        and_(
            UserData.admin,
            UserData.active != UserActivity.banned,
            UserData.active != UserActivity.deleted,
        )
    )

    return (await execute_query(query)).scalars().all()
