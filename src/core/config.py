"""Основная конфигурация (настройки, параметры) приложения"""

import logging
import os
from datetime import datetime

from pandas import DataFrame
from pydantic import HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.orm import DeclarativeBase

from core.path import PATH

logger = logging.getLogger()


class AuthorizeVar(BaseSettings):
    """Класс для хранения параметров авторизации yoomoney."""

    client_id: SecretStr
    """Идентификатор клиента yoomoney."""
    client_secret: SecretStr
    """Секрет клиента yoomoney."""


class Base(DeclarativeBase):
    """Базовый класс для моделей SQLAlchemy."""

    def __repr__(self):
        """Строковое представление экземпляра модели.

        Returns:
            str: Строковое представление.
        """
        cols = [f"{col}={getattr(self, col)}" for col in self.__table__.columns.keys()]
        return f"<{self.__class__.__name__} {', '.join(cols)}>"

    @property
    def __udict__(self):
        """Возвращает словарь атрибутов модели.

        Returns:
            dict: Словарь с данными модели.
        """
        model_data = {col: getattr(self, col) for col in self.__table__.columns.keys()}
        return model_data

    @property
    def __ustr_dict__(self):
        """Возвращает словарь атрибутов модели в виде строк.

        Returns:
            dict: Словарь с данными модели в виде строк.
        """
        model_data = {
            col: str(getattr(self, col)) for col in self.__table__.columns.keys()
        }
        return model_data

    @property
    def frame(self):
        """Возвращает DataFrame с данными модели.

        Returns:
            DataFrame: DataFrame с данными модели.
        """
        return DataFrame([self.__udict__]).dropna(how="all")

    def get_frame(self, *objects):
        """Возвращает DataFrame для переданных объектов.

        Args:
            *objects: Объекты для извлечения данных.

        Returns:
            DataFrame: DataFrame с данными объектов.
        """
        res = []
        for obj in objects:
            if type(obj) is type(self):
                res.append(obj.__udict__)
            else:
                res.append(self.__udict__)
        return DataFrame(res).dropna(how="all")


class Settings(BaseSettings):
    """Класс для хранения настроек приложения."""

    BOT_TOKEN: SecretStr
    """Токен бота."""
    YOO_TOKEN: SecretStr
    """Токен Yoomoney."""

    BOT_CHAT: int
    """ID чата бота."""
    BOT_URL: HttpUrl = "https://t.me/vpn_dan_bot"
    """URL бота."""
    subserver_url: HttpUrl = "http:/assa.ddns.net"
    """URL подсервера."""

    DB_HOST: str
    """Хост базы данных."""
    DB_PORT: int
    """Порт базы данных."""
    DB_USER: str
    """Имя пользователя базы данных."""
    DB_PASS: SecretStr
    """Пароль базы данных."""
    DB_NAME: str
    """Имя базы данных."""

    ADMIN_LOGIN: str
    """Логин администратора."""
    ADMIN_PASS: SecretStr
    """Пароль администратора."""
    ADMIN_HASH: SecretStr
    """Хеш пароля администратора."""
    JWT_SECRET: SecretStr
    """Секрет для JWT."""
    ALGORITHM: str
    """Алгоритм шифрования jwt токена"""
    

    WG_HOST: str
    """Хост WireGuard."""
    WG_PORT: int
    """Порт WireGuard."""
    WG_USER: str
    """Имя пользователя WireGuard."""
    WG_PASS: SecretStr
    """Пароль WireGuard."""
    WG_KEY: SecretStr
    """Ключ WireGuard."""
    WG_SERVER_KEY: str
    """Ключ сервера WireGuard."""

    REDIS_HOST: str
    """Хост Redis."""
    REDIS_PORT: int
    """Порт Redis."""
    REDIS_USER: str
    """Имя пользователя Redis."""
    REDIS_PASS: SecretStr
    """Пароль Redis."""
    REDIS_NAME: str
    """Имя базы данных Redis."""

    acceptable_config: dict = {0: 0, 0.3: 1, 1: 3, 2.5: 8, 5: 15}
    """Допустимое количество конфигураций для разных тарифов."""
    cost: float
    """Стоимость подписки."""
    cash_ttl: int
    """Время жизни кэша."""
    transfer_fee: float
    """Комиссия за перевод."""
    max_dumps: int
    """Максимальное количество дампов."""

    model_config = SettingsConfigDict(
        env_file=os.path.join(PATH, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def DATABASE_URL(self) -> str:
        """URL для подключения к базе данных.

        Returns:
            str: URL подключения к базе данных в формате
            postgresql+asyncpg://username:password@localhost:port/base
        """
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS.get_secret_value()}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def CASHBASE_URL(self) -> str:
        """URL для подключения к базе данных Redis.

        Returns:
            str: URL подключения к Redis в формате
            redis://LOGIN:PASSWORD@HOST:PORT/NUM_DB
        """
        return f"redis://{self.REDIS_USER}:{self.REDIS_PASS.get_secret_value()}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_NAME}"


try:
    settings = Settings()

except ValueError:
    logger.exception("Ошибка загрузки входных параметров")
    raise


last_updated = datetime.today()
"""Время последнего запуска"""
decr_time = os.path.join(PATH, "src", "scheduler", "last_decremented.pickle")
"""Сериализованная дата последнего списания средств"""
noticed_time = os.path.join(PATH, "src", "scheduler", "last_noticed.pickle")
"""Сериализованная дата последнего уведомления пользователей"""

# for timefile in (decr_time, noticed_time):
#     with open(timefile, "wb") as file:
#         pickle.dump(last_updated, file)
