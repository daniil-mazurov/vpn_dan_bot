"""
Модуль базы данных.

Этот модуль содержит схемы таблиц базы данных и перечисления, используемые в проекте.
Он импортирует необходимые модели и определяет структуру базы данных.

Импортируемые модели:
- UserData: Модель данных пользователя.
- Transactions: Модель транзакций.
- WgConfig: Модель конфигурации WireGuard.
- Reports: Модель отчетов.
- YoomoneyOperation: Модель операции YooMoney.
- YoomoneyOperationDetails: Модель деталей операции YooMoney.
- News: Модель новостей.

Перечисления:
- FreezeSteps: Шаги заморозки.
- ReportStatus: Статусы отчетов.
- UserActivity: Статусы активности пользователей.
- Notifications: Типы уведомлений.

Словарь TABLES_SCHEMA сопоставляет названия таблиц с их соответствующими моделями.

Attributes:
    TABLES_SCHEMA (dict): Словарь, где ключами являются названия таблиц,
    а значениями - соответствующие модели.
"""

from core.config import Base
from db import ddl as _  # NOTE TRIGGERS
from db.models.enums import (FreezeSteps, NotificationType, ReportStatus,
                             UserActivity)
from db.models.news import News
from db.models.notifications import Notifications
from db.models.reports import Reports
from db.models.transactions import Transactions
from db.models.userdata import UserData
from db.models.wg_config import WgConfig
from db.models.yoomoney import (YoomoneyOperation, YoomoneyOperationDetails,
                                yoomoney_site_display)

TABLES_SCHEMA = {
    UserData.__tablename__: UserData,
    Transactions.__tablename__: Transactions,
    WgConfig.__tablename__: WgConfig,
    Reports.__tablename__: Reports,
    YoomoneyOperation.__tablename__: YoomoneyOperation,
    News.__tablename__: News,
    Notifications.__tablename__: Notifications,
}
