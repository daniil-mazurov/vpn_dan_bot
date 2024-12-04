from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from fastui.components.display import DisplayLookup, DisplayMode
from fastui.events import GoToEvent
from pydantic import (BaseModel, ConfigDict, Field, field_validator,
                      model_validator)
from sqlalchemy import BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.config import Base


class Transactions(Base):
    """Модель транзакций.

    Эта модель представляет собой структуру данных для хранения информации
    о транзакциях пользователей.
    """

    __tablename__ = "transactions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    """int: Уникальный идентификатор транзакции."""

    user_id: Mapped[int] = mapped_column(
        ForeignKey("userdata.telegram_id", ondelete="CASCADE"), type_=BigInteger
    )
    """int: Идентификатор пользователя в Telegram, связанный с транзакцией."""

    date: Mapped[datetime] = mapped_column(type_=DateTime(timezone=True))
    """datetime: Дата и время транзакции с учетом часового пояса."""

    amount: Mapped[float]
    """float: Сумма транзакции."""

    label: Mapped[UUID]
    """UUID: Метка транзакции."""

    # PAYED
    transaction_id: Mapped[str | None]
    """str | None: Идентификатор транзакции (по умолчанию None)."""

    sha1_hash: Mapped[str | None]
    """str | None: SHA-1 хэш транзакции (по умолчанию None)."""

    sender: Mapped[str | None]
    """str | None: Отправитель транзакции (по умолчанию None)."""

    withdraw_amount: Mapped[float | None]
    """float | None: Сумма вывода (по умолчанию None)."""

    # additionally
    transaction_reference: Mapped[str]
    """str: Ссылка на транзакцию."""

    transact_connect: Mapped["UserData"] = relationship(  # noqa: F821 # type: ignore
        back_populates="transactions", lazy="subquery"
    )
    """UserData: Связанные транзакции пользователя"""

    class ValidationSchema(BaseModel):
        """Схема валидации для модели транзакций.

        Эта схема используется для валидации данных, связанных с транзакциями.
        """

        id: int | None = Field(default=None, title="ID")
        """Уникальный идентификатор транзакции."""

        user_id: int | None = Field(default=None, title="Telegram ID")
        """Идентификатор пользователя в Telegram (по умолчанию None)."""

        date: datetime = Field(title="Transaction date")
        """Дата и время транзакции."""

        amount: float = Field(title="Amount")
        """Сумма транзакции."""

        label: UUID = Field(title="Label")
        """Метка транзакции."""

        transaction_id: str | None = Field(default=None, title="Transaction ID")
        """Идентификатор транзакции (по умолчанию None)."""

        sha1_hash: str | None = Field(default=None, title="Hash")
        """SHA-1 хэш транзакции (по умолчанию None)."""

        sender: str | None = Field(default=None, title="Sender")
        """Отправитель транзакции (по умолчанию None)."""

        withdraw_amount: float | None = Field(default=None, title="Withdraw_amount")
        """Сумма вывода (по умолчанию None)."""

        transaction_reference: str | None = Field(
            default=None, title="Transaction Reference"
        )
        """Ссылка на транзакцию (по умолчанию None)."""

        site_date: str = Field(init=False, title="Transaction date", default="00:00")
        """Строковое представление даты транзакции (не инициализируется при создании)."""

        @field_validator("amount", "withdraw_amount")
        def round_amount(cls, v):
            """Сумма транзакции (округленная)."""
            return round(v, 2)

        @model_validator(mode="before")
        def convert_str_to_none(cls, values):
            """Преобразует строки 'None' в None.

            Args:
                cls: Класс схемы.
                values: Значения для валидации.

            Returns:
                dict: Обновленные значения.
            """
            if isinstance(values, Iterable):
                return {k: None if v == "None" else v for k, v in dict(values).items()}
            return values

        @model_validator(mode="after")
        def set_site_date(cls, values: BaseModel):
            """Устанавливает строковое представление даты транзакции.

            Args:
                cls: Класс схемы.
                values (BaseModel): Значения для валидации.

            Returns:
                BaseModel: Обновленные значения.
            """
            if hasattr(values, "date"):
                values.site_date = values.date.astimezone().ctime()
            return values

        model_config = ConfigDict(extra="ignore")

    # INTERFACE (fastui)
    site_display = [
        DisplayLookup(field="id"),
        DisplayLookup(
            field="user_id",
            mode=DisplayMode.plain,
            on_click=GoToEvent(url="/bot/tables/userdata/?telegram_id={user_id}"),
        ),
        DisplayLookup(field="site_date"),
        DisplayLookup(field="amount"),
        DisplayLookup(
            field="label",
            on_click=GoToEvent(url="/bot/tables/transactions/?label={label}"),
        ),
    ]
    """list[DisplayLookup]: Отображение транзакций на сайте."""

    site_display_all = site_display + [
        DisplayLookup(field="sender"),
        DisplayLookup(field="transaction_id", mode=DisplayMode.plain),
        DisplayLookup(field="sha1_hash", mode=DisplayMode.inline_code),
        DisplayLookup(field="withdraw_amount"),
    ]
    """list[DisplayLookup]: Полное отображение транзакций на сайте."""

    def __init__(self, **kwargs):
        """Инициализирует модель транзакций.

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
