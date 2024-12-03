from datetime import date as date_cls
from datetime import datetime

from fastui.components.display import DisplayLookup, DisplayMode
from fastui.events import GoToEvent
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.config import Base
from db.models import ReportStatus


class Reports(Base):
    """Модель отчетов.

    Эта модель представляет собой структуру данных для хранения отчетов,
    связанных с пользователями.
    """

    __tablename__ = "reports"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    """int: Уникальный идентификатор отчета."""

    user_id: Mapped[int] = mapped_column(
        ForeignKey("userdata.telegram_id", ondelete="CASCADE"), type_=BigInteger
    )
    """int: Идентификатор пользователя в Telegram, связанный с отчетом."""

    user_name: Mapped[str | None] = mapped_column(default=None)
    """str | None: Имя пользователя, связанное с отчетом (по умолчанию None)."""

    info: Mapped[str]
    """str: Информация о отчете."""

    pictures: Mapped[dict | None] = mapped_column(type_=JSONB, default=None)
    """dict | None: Словарь с изображениями, связанными с отчетом (по умолчанию None)."""

    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ReportStatus.created,
    )
    """ReportStatus: Статус отчета (по умолчанию 'создан')."""

    create_date: Mapped[date_cls] = mapped_column(type_=Date, server_default=func.now())
    """date_cls: Дата создания отчета (по умолчанию - текущая дата)."""

    updated: Mapped[datetime] = mapped_column(
        type_=DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.current_timestamp(),
    )
    """datetime: Дата и время последнего обновления отчета."""

    rep_connect: Mapped["UserData"] = relationship(  # noqa: F821 # type: ignore
        back_populates="reports", lazy="subquery"
    )
    """UserData: Связанные обращения пользователя"""

    class ValidationSchema(BaseModel):
        """Схема валидации для модели отчетов.

        Эта схема используется для валидации данных, связанных с отчетами.
        """

        id: int | None = Field(default=None, title="ID")
        """Уникальный идентификатор отчета."""

        user_id: int = Field(title="Telegram ID")
        """Идентификатор пользователя в Telegram."""

        user_name: str | None = Field(default=None, title="Name")
        """Имя пользователя."""

        info: str = Field(title="Info")
        """Информация о отчете."""

        pictures: dict | None = Field(default={}, title="Pictures")
        """Словарь с изображениями, связанными с отчетом."""

        status: ReportStatus = Field(default=ReportStatus.created, title="Status")
        """Статус отчета."""

        create_date: date_cls = Field(title="Create date")
        """Дата создания отчета."""

        updated: datetime | None = Field(default=None, title="Last update")
        """Дата и время последнего обновления отчета."""

        site_updated: str = Field(init=False, title="Last update", default="00:00")
        """Строковое представление последнего обновления (не инициализируется при создании)."""

        @model_validator(mode="after")
        def set_updated(cls, values: BaseModel):
            """Устанавливает строковое представление последнего обновления.

            Args:
                cls: Класс схемы.
                values (BaseModel): Значения для валидации.

            Returns:
                BaseModel: Обновленные значения.
            """
            if hasattr(values, "updated") and hasattr(values.updated, "ctime"):
                values.site_updated = values.updated.astimezone().ctime()
            return values

        model_config = ConfigDict(extra="ignore")

    # INTERFACE (fastui)
    site_display = [
        DisplayLookup(
            field="id",
            on_click=GoToEvent(
                url="/bot/tables/reports/?report_id={id}&telegram_id={user_id}"
            ),
        ),
        DisplayLookup(
            field="user_id",
            mode=DisplayMode.plain,
            on_click=GoToEvent(url="/bot/tables/userdata/?telegram_id={user_id}"),
        ),
        DisplayLookup(field="user_name", mode=DisplayMode.as_title),
        DisplayLookup(field="status"),
        DisplayLookup(field="create_date", mode=DisplayMode.date),
    ]
    """list[DisplayLookup]: Отображение отчетов на сайте."""

    site_display_all = site_display + [
        DisplayLookup(field="site_updated"),
        DisplayLookup(field="info"),
    ]
    """list[DisplayLookup]: Полное отображение отчетов на сайте."""

    def __init__(self, **kwargs):
        """Инициализирует модель отчетов.

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
