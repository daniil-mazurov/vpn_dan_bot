from datetime import datetime

from fastui.components.display import DisplayLookup, DisplayMode
from fastui.events import GoToEvent
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.config import Base
from db.models import NotificationType


class Notifications(Base):
    """Модель уведомлений.

    Эта модель представляет собой структуру данных для хранения уведомлений,
    включая тип уведомления, содержание и другие атрибуты.
    """

    __tablename__ = "notifications"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    """int: Уникальный идентификатор уведомления."""

    user_id: Mapped[int] = mapped_column(
        ForeignKey("userdata.telegram_id", ondelete="CASCADE"), type_=BigInteger
    )
    """int: Идентификатор пользователя в Telegram, связанный с уведомлением."""

    type: Mapped[NotificationType]
    "NotificationType: тип уведомления"

    message: Mapped[str]
    """str: Содержание уведомления."""

    date: Mapped[datetime] = mapped_column(
        type_=DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.current_timestamp(),
    )
    """datetime: Дата создания уведомления (по умолчанию - текущая дата)."""

    notif_connect: Mapped["UserData"] = relationship(  # noqa: F821 # type: ignore
        back_populates="notifications", lazy="subquery"
    )
    """UserData: Связанные уведомления пользователя"""

    class ValidationSchema(BaseModel):
        """Схема валидации для модели уведомлений.

        Эта схема используется для валидации данных, связанных с уведомлениями.
        """

        id: int | None = Field(default=None, title="ID")
        """Уникальный идентификатор уведомления."""

        user_id: int = Field(title="Telegram ID")
        """Идентификатор пользователя в Telegram."""

        type: NotificationType = Field(title="Notification Type")
        """Тип уведомления."""

        message: str = Field(title="Message")
        """Заголовок уведомления."""

        date: datetime = Field(title="Create date")
        """Дата создания уведомления."""

        model_config = ConfigDict(extra="ignore")

    # INTERFACE (fastui)
    site_display = [
        DisplayLookup(
            field="id",
            on_click=GoToEvent(url="/bot/tables/notifications/?notification_id={id}"),
        ),
        DisplayLookup(field="type"),
        DisplayLookup(field="message"),
        DisplayLookup(field="date", mode=DisplayMode.datetime),
    ]
    """list[DisplayLookup]: Отображение уведомлений на сайте."""

    site_display_all = site_display
    """list[DisplayLookup]: Полное отображение уведомлений на сайте."""

    def __init__(self, **kwargs):
        """Инициализирует модель уведомлений.

        Args:
            **kwargs: Дополнительные параметры для инициализации модели.
        """
        if kwargs:
            validated_data = self.ValidationSchema(**kwargs).model_dump(
                exclude={"site_date"}
            )
            super().__init__(**(validated_data))
        else:
            super().__init__(**(kwargs))
