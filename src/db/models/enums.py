import enum


class UserActivity(enum.Enum):
    """Статус пользователя"""

    active = "active"
    """Пользователь активен"""
    inactive = "inactive"
    """Пользователь неактивен"""
    freezed = "freezed"
    """Пользователь заморожен"""
    deleted = "deleted"
    """Пользователь удален"""
    banned = "banned"
    """Пользователь заблокирован"""

    def __str__(self) -> str:
        """Возвращает строковое представление состояния активности пользователя.

        Returns:
            str: Строковое представление состояния активности.
        """
        return self.value


class FreezeSteps(enum.Enum):
    """Статус заморозки конфигурации"""

    yes = "yes"
    """Заморозка подтверждена"""
    wait_yes = "wait_yes"
    """Ожидание подтверждения заморозки"""
    no = "no"
    """Заморозка отклонена"""
    wait_no = "wait_no"
    """Ожидание отклонения заморозки"""

    def __str__(self) -> str:
        """Возвращает строковое представление шага заморозки.

        Returns:
            str: Строковое представление шага заморозки.
        """
        return self.value


class ReportStatus(enum.Enum):
    """Статус обращения"""

    created = "created"
    """Обращение создано"""
    at_work = "at_work"
    """Обращение в работе"""
    decided = "decided"
    """Обращение решено"""
    cancelled = "cancelled"
    """Обращение отменено"""

    def __str__(self) -> str:
        """Возвращает строковое представление статуса отчета.

        Returns:
            str: Строковое представление статуса отчета.
        """
        return self.value


class NotificationType(enum.Enum):
    """Тип уведомления"""

    success = "success"
    """Уведомление об успешной операции"""
    error = "error"
    """Уведомление об ошибочной операции"""
    warning = "warning"
    """Важно уведомление"""
    info = "info"
    """Информация для пользователя"""

    def __str__(self) -> str:
        """Возвращает строковое представление типа уведомления.

        Returns:
            str: Строковое представление типа уведомления.
        """
        return self.value
