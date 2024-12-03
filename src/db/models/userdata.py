from datetime import datetime

from fastui.components.display import DisplayLookup, DisplayMode
from fastui.events import GoToEvent
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import BigInteger, DateTime, Enum, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.config import Base
from db.models import UserActivity
from db.models.notifications import Notifications
from db.models.reports import Reports
from db.models.transactions import Transactions
from db.models.wg_config import WgConfig


class UserData(Base):
    """Модель данных пользователя.

    Эта модель представляет собой структуру данных для хранения информации
    о пользователях, включая их настройки, баланс и статус.
    """

    __tablename__ = "userdata"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    """int: Уникальный идентификатор пользователя."""

    telegram_id: Mapped[int] = mapped_column(type_=BigInteger, unique=True)
    """int: Идентификатор пользователя в Telegram (уникальный)."""

    telegram_name: Mapped[str]
    """str: Имя пользователя в Telegram."""

    admin: Mapped[bool] = mapped_column(default=False)
    """bool: Является ли пользователь администратором (по умолчанию False)."""

    active: Mapped[UserActivity] = mapped_column(
        Enum(UserActivity, values_callable=lambda obj: [e.value for e in obj]),
        default=UserActivity.inactive,
    )
    """UserActivity: Статус активности пользователя (по умолчанию неактивен)."""

    stage: Mapped[float] = mapped_column(default=0)
    """float: Этап пользователя (по умолчанию 0)."""

    balance: Mapped[float] = mapped_column(type_=Numeric(scale=2), default=0)
    """float: Баланс пользователя (по умолчанию 0)."""

    free: Mapped[bool] = mapped_column(default=True)
    """bool: Доступен ли пользователь (по умолчанию True)."""

    mute: Mapped[bool] = mapped_column(server_default="0")
    """bool: Заглушен ли пользователь (по умолчанию False)."""

    updated: Mapped[datetime] = mapped_column(
        type_=DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.current_timestamp(),
    )
    """datetime: Дата и время последнего обновления пользователя."""

    configs: Mapped[list["WgConfig"]] = relationship(
        back_populates="conf_connect", lazy="subquery"
    )
    """list[WgConfig]: Связанные конфигурации WG пользователя."""

    transactions: Mapped[list["Transactions"]] = relationship(
        back_populates="transact_connect", lazy="subquery"
    )
    """list[Transactions]: Связанные транзакции пользователя."""

    reports: Mapped[list["Reports"]] = relationship(
        back_populates="rep_connect", lazy="subquery"
    )
    """list[Reports]: Связанные обращения пользователя."""

    notifications: Mapped[list["Notifications"]] = relationship(
        back_populates="notif_connect", lazy="subquery"
    )
    """list[Notifications]: Связанные уведомления пользователя."""

    # @hybrid_property
    def fbalance(self):
        """Возвращает округленный баланс пользователя.

        Returns:
            float: Округленный баланс пользователя.
        """
        return round(float(self.balance), 2)

    class ValidationSchema(BaseModel):
        """Схема валидации для модели данных пользователя.

        Эта схема используется для валидации данных, связанных с пользователями.
        """

        id: int | None = Field(default=None, title="ID")
        """Уникальный идентификатор пользователя."""

        telegram_id: int = Field(title="Telegram ID")
        """Идентификатор пользователя в Telegram."""

        telegram_name: str = Field(title="Name")
        """Имя пользователя в Telegram."""

        admin: bool = Field(title="Admin", default=False)
        """Является ли пользователь администратором (по умолчанию False)."""

        active: UserActivity = Field(title="Active", default=UserActivity.inactive)
        """Статус активности пользователя (по умолчанию неактивен)."""

        stage: float = Field(title="Stage", default=0)
        """Этап пользователя (по умолчанию 0)."""

        balance: float = Field(title="Balance", default=0)
        """Баланс пользователя (по умолчанию 0)."""

        free: bool = Field(title="Free", default=True)
        """Доступен ли пользователь (по умолчанию True)."""

        mute: bool = Field(title="Mute", default=False)
        """Заглушен ли пользователь (по умолчанию False)."""

        updated: datetime = Field(title="Last update")
        """Дата и время последнего обновления пользователя."""

        configs: list["WgConfig.ValidationSchema"] = Field(
            default=[], title="User Configurations"
        )
        """Конфигурации пользователя."""

        site_updated: str = Field(init=False, title="Last update", default="00:00")
        """Строковое представление последнего обновления (не инициализируется при создании)."""

        @model_validator(mode="after")
        def set_site_date(cls, values: BaseModel):
            """Устанавливает строковое представление даты последнего обновления.

            Args:
                cls: Класс схемы.
                values (BaseModel): Значения для валидации.

            Returns:
                BaseModel: Обновленные значения.
            """
            if hasattr(values, "updated"):
                values.site_updated = values.updated.astimezone().ctime()
            return values

        model_config = ConfigDict(extra="ignore")

    class ValidationSchemaExtended(ValidationSchema):
        transactions: list["Transactions.ValidationSchema"] = Field(
            default=[], title="User Transactions"
        )
        """Транзакции пользователя."""

        reports: list["Reports.ValidationSchema"] = Field(
            default=[], title="User Reports"
        )
        """Обращения пользователя."""

        notifications: list["Notifications.ValidationSchema"] = Field(
            default=[], title="User Notifications"
        )
        """Уведомления пользователя."""

    # INTERFACE (fastui)
    site_display = [
        DisplayLookup(field="id"),
        DisplayLookup(
            field="telegram_id",
            mode=DisplayMode.plain,
            on_click=GoToEvent(url="/bot/tables/userdata/?telegram_id={telegram_id}"),
        ),
        DisplayLookup(field="telegram_name", mode=DisplayMode.as_title),
        DisplayLookup(field="admin"),
        DisplayLookup(field="active", mode=DisplayMode.markdown),
        DisplayLookup(field="stage"),
        DisplayLookup(field="balance"),
        DisplayLookup(field="free"),
        DisplayLookup(field="mute"),
        DisplayLookup(field="site_updated"),
    ]
    """list[DisplayLookup]: Отображение данных пользователя на сайте."""

    def __init__(self, **kwargs):
        """Инициализирует модель данных пользователя.

        Args:
            **kwargs: Дополнительные параметры для инициализации модели.
        """
        if kwargs:
            validated_data = self.ValidationSchema(**kwargs).model_dump(
                exclude={"site_updated"}
            )
            super().__init__(**(validated_data))
        else:
            super().__init__(**(kwargs))
