from datetime import datetime

from fastui.components.display import DisplayLookup
from fastui.events import GoToEvent
from pydantic import BaseModel, Field, model_validator


class YoomoneyOperation(BaseModel):
    """Модель операции YooMoney.

    Эта модель представляет собой структуру данных для хранения информации
    об операциях YooMoney.
    """

    __tablename__ = "yoomoney"

    operation_id: str
    """Уникальный идентификатор операции."""

    status: str
    """Статус операции."""

    datetime: datetime
    """Дата и время операции."""

    title: str
    """Заголовок операции."""

    pattern_id: str | None = None
    """Идентификатор шаблона операции (по умолчанию None)."""

    direction: str
    """Направление операции (например, 'incoming' или 'outgoing')."""

    amount: float
    """Сумма операции."""

    label: str | None = None
    """Метка операции."""

    type: str
    """Тип операции."""

    site_datetime: str = Field(init=False, title="Datetime", default="00:00")
    """Строковое представление даты и времени операции (не инициализируется при создании)."""

    @model_validator(mode="after")
    def set_date(cls, values: BaseModel):
        """Устанавливает строковое представление даты операции.

        Args:
            cls: Класс схемы.
            values (BaseModel): Значения для валидации.

        Returns:
            BaseModel: Обновленные значения.
        """
        if hasattr(values, "datetime"):
            values.site_datetime = values.datetime.astimezone().ctime()
        return values


class YoomoneyOperationDetails(BaseModel):
    """Модель деталей операции YooMoney.

    Эта модель представляет собой структуру данных для хранения подробной информации
    об операциях YooMoney.
    """

    operation_id: str
    """Уникальный идентификатор операции."""

    status: str
    """Статус операции."""

    pattern_id: str | None = None
    """Идентификатор шаблона операции (по умолчанию None)."""

    direction: str
    """Направление операции (например, 'incoming' или 'outgoing')."""

    amount: float
    """Сумма операции."""

    amount_due: str | None = None
    """Сумма, подлежащая оплате (по умолчанию None)."""

    fee: float | None = None
    """Комиссия за операцию (по умолчанию None)."""

    answer_datetime: datetime | None = None
    """Дата и время ответа (по умолчанию None)."""

    datetime: datetime
    """Дата и время операции."""

    title: str
    """Заголовок операции."""

    sender: str | None = None
    """Отправитель операции (по умолчанию None)."""

    recipient: str | None = None
    """Получатель операции (по умолчанию None)."""

    recipient_type: str | None = None
    """Тип получателя (по умолчанию None)."""

    message: str | None = None
    """Сообщение, связанное с операцией (по умолчанию None)."""

    comment: str | None = None
    """Комментарий к операции (по умолчанию None)."""

    codepro: bool | None = None
    """Указывает, защищена ли операция с помощью CodePro (по умолчанию None)."""

    protection_code: str | None = None
    """Код защиты операции (по умолчанию None)."""

    expires: str | None = None
    """Срок действия операции (по умолчанию None)."""

    label: str | None = None
    """Метка операции."""

    details: str | None = None
    """Дополнительные детали операции (по умолчанию None)."""

    type: str
    """Тип операции."""

    digital_goods: str | None = None
    """Цифровые товары, связанные с операцией (по умолчанию None)."""

    @model_validator(mode="before")
    def convert_ints_to_str(cls, values):
        """Преобразует целые числа в строки.

        Args:
            cls: Класс схемы.
            values: Значения для валидации.

        Returns:
            dict: Обновленные значения.
        """
        return {
            k: str(v) if isinstance(v, int) else v for k, v in values.__dict__.items()
        }

    site_datetime: str = Field(init=False, title="Datetime", default="00:00")
    """Строковое представление даты и времени операции (не инициализируется при создании)."""

    @model_validator(mode="after")
    def set_date(cls, values: BaseModel):
        """Устанавливает строковое представление даты операции.

        Args:
            cls: Класс схемы.
            values (BaseModel): Значения для валидации.

        Returns:
            BaseModel: Обновленные значения.
        """
        if hasattr(values, "datetime"):
            values.site_datetime = values.datetime.astimezone().ctime()
        return values


yoomoney_site_display: list = [
    DisplayLookup(
        field="operation_id",
        on_click=GoToEvent(url="/bot/tables/yoomoney/?operation_id={operation_id}"),
    ),
    DisplayLookup(field="status"),
    DisplayLookup(field="site_datetime"),
    DisplayLookup(field="title"),
    DisplayLookup(field="amount"),
    DisplayLookup(field="label"),
]
"""list: Отображение операций YooMoney на сайте."""
