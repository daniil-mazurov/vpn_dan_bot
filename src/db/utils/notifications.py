"""Функционал для работы с БД. Работа с пользовательскими уведомлениями"""

import logging

from sqlalchemy import desc, insert, select

from core.metric import async_speed_metric
from db.database import execute_query
from db.models import Notifications

logger = logging.getLogger()


@async_speed_metric
async def get_notifications(user_id):
    # result: Notifications = await CashManager(Notifications).get({user_id: ...})
    # if result:
    #     return result[0]

    query = (
        select(Notifications)
        .where(Notifications.user_id == user_id)
        .order_by(desc(Notifications.date))
    )
    result: list[Notifications] = (await execute_query(query)).scalars().all()

    # if result:
    #     await CashManager(Notifications).add({user_id: result.__ustr_dict__})

    return result


@async_speed_metric
async def add_notification(notification: Notifications.ValidationSchema):
    # await CashManager(Notifications).delete(user_id)

    query = (
        insert(Notifications).values(notification.model_dump(exclude='id')).returning(Notifications)
    )

    return (await execute_query(query)).scalar_one_or_none()
