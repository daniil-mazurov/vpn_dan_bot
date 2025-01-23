"""Функционал для работы с Redis."""

import logging
from collections.abc import Iterable, Mapping
from datetime import timedelta
from types import NoneType
from typing import Union

from core.config import settings
from core.exceptions import RedisTypeError
from db.database import execute_redis_query, iter_redis_keys, redis_engine
from db.models import Transactions, UserData, WgConfig

logger = logging.getLogger("redis")


class CashManager:
    """Менеджер для работы с кэшем в Redis."""

    class user_id:
        """Класс для аннотации типов."""

    redis_types = (bytes, str, int, float, NoneType)
    """Допустимые типы данных для хранения в Redis."""

    def __init__(
        self, validation_model: Union[UserData, WgConfig, Transactions]
    ) -> None:
        """Инициализирует CashManager.

        Args:
            validation_model (Union[UserData, WgConfig, Transactions]): Модель для валидации данных.
        """
        self.pipe = redis_engine.pipeline()
        self.model = validation_model

    @property
    def cmd(self):
        """Доступ к redis pipeline для выполнения команд.

        Returns:
            Pipeline: Текущий Redis pipeline.
        """
        return self.pipe

    async def __call__(self):
        """Выполняет команды Redis и возвращает результаты.

        Returns:
            list: Список объектов модели, представляющих результаты выполнения команд.
        """
        results = await execute_redis_query(self.pipe)

        validated_results = []
        for result in results:
            if result and isinstance(result, (dict, str, tuple, list)):
                match result:
                    case Mapping():
                        validated_results.append(self.model(**result))
                    case Iterable():
                        validated_results.append(self.model(*result))
                    case _:
                        validated_results.append(self.model(result))

        if len(validated_results):
            return validated_results

    def converter(self, data):
        """Преобразует данные в допустимые типы для Redis.

        Args:
            data (Union[dict, list, tuple, set]): Данные для преобразования.

        Returns:
            Union[dict, list, set]: Преобразованные данные.
        """
        match data:
            case dict():
                return {
                    key: (value if type(value) in self.redis_types else str(value))
                    for key, value in data.items()
                }
            case list() | tuple():
                return [
                    value if type(value) in self.redis_types else str(value)
                    for value in data
                ]
            case set():
                return {
                    value if type(value) in self.redis_types else str(value)
                    for value in data
                }
            case _:
                return data

    async def add(
        self,
        key_map: dict[user_id, dict | list | tuple | set | str | int | float] = None,
        **mapping: dict[user_id, dict | list | tuple | set | str | int | float],
    ):
        """Добавляет данные в Redis.

        Args:
            key_map (dict, optional): Словарь ключей и значений для добавления.
            **mapping (dict): Дополнительные ключи и значения для добавления.

        Examples:
            add({user_id: {data}})
        """
        for key, item in key_map.items() if key_map else mapping.items():
            if not item:
                return
            item = self.converter(item)
            key = f"data:{self.model.__tablename__}:{key}"

            match item:
                case dict():
                    self.pipe.hset(name=key, mapping=item)
                case list() | tuple():
                    self.pipe.rpush(key, *item)
                case set():
                    self.pipe.sadd(key, *item)
                case str() | int() | float():
                    self.pipe.set(name=key, value=item)

                case _:
                    raise RedisTypeError

            self.pipe.expire(key, timedelta(hours=settings.cash_ttl))
        await execute_redis_query(self.pipe)

    async def get(self, *id_obj: dict | list | tuple | set | str | int | float):
        """Получает данные из Redis по заданным ключам.

        Args:
            *id_obj (Union[dict, list, tuple, set, str, int, float]): Ключи для получения данных.

        Returns:
            list: Список объектов модели, представляющих полученные данные.
        """
        for key in id_obj:
            match key:
                case dict():
                    self.pipe.hgetall(f"data:{self.model.__tablename__}:{list(key)[0]}")
                case list() | tuple():
                    self.pipe.lrange(f"data:{self.model.__tablename__}:{key[0]}", 0, -1)
                case set():
                    self.pipe.smembers(name=f"data:{self.model.__tablename__}:{key[0]}")
                case str() | int() | float():
                    self.pipe.get(name=f"data:{self.model.__tablename__}:{key}")

                case _:
                    raise RedisTypeError

        return await self.__call__()

    async def delete(self, *keys, fullkey=False):
        """Удаляет данные из Redis по заданным ключам.

        Args:
            *keys (str): Ключи для удаления данных.
            fullkey (bool, optional): Указывает, нужно ли использовать полные ключи. По умолчанию False.

        Returns:
            list: Список объектов модели, представляющих удаленные данные.
        """
        if not fullkey:
            keys = [f"data:{self.model.__tablename__}:{key}" for key in keys]
        if keys:
            self.pipe.delete(*keys)
            return await self.__call__()

    async def clear(self, user_id, fullkey=False):
        """Очищает данные из Redis для указанного пользователя.

        Args:
            user_id (str): Идентификатор пользователя.
            fullkey (bool, optional): Указывает, нужно ли использовать полные ключи. По умолчанию False.

        Returns:
            list: Список объектов модели, представляющих очищенные данные.
        """
        if not fullkey:
            rkeys = []
            pattern = ":*"
            for n in range(1, 4):
                async for key in await iter_redis_keys(f"data{pattern * n}:{user_id}"):
                    rkeys.append(key)
        if rkeys:
            self.pipe.delete(*rkeys)
            return await self.__call__()
