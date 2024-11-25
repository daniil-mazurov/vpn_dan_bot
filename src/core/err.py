"""Функционал обработки ошибок"""

import logging
import os
from collections import deque
from functools import wraps

from aiogram.exceptions import AiogramError, TelegramNetworkError
from redis import exceptions as rexc
from redis.asyncio.client import Pipeline

from core.exceptions import DatabaseError

ERRORS = deque([], maxlen=5)

logger = logging.getLogger()
rLogger = logging.getLogger("redis")


def log_cash_error(error: Exception):
    error_info = {"type": type(error).__name__, "message": str(error)}

    if error_info not in ERRORS:
        ERRORS.append(error_info)

        return True


def get_args_dict(fn, args, kwargs):
    """Создает словарь аргументов для функции.

    Args:
        fn (function): Функция, для которой необходимо получить аргументы.
        args (tuple): Позиционные аргументы функции.
        kwargs (dict): Именованные аргументы функции.

    Returns:
        dict: Словарь аргументов, где ключи - имена параметров, а значения - переданные значения.
    """
    args_names = fn.__code__.co_varnames[: fn.__code__.co_argcount]
    return {**dict(zip(args_names, args)), **kwargs}


def exception_logging(
    ignore_raise=False,
    custom_exception=Exception,
    message="Something went wrong",
):
    """Декоратор для логирования исключений, возникающих в синхронных функциях.

    Args:
        ignore_raise (bool, optional): Прерывать ли выполнение программы при возникновении исключения. Defaults to False.
        custom_exception (Exception, optional): Тип исключения, который нужно обрабатывать. Defaults to Exception.
        message (str, optional): Сообщение для логирования при возникновении исключения. Defaults to "Something went wrong".

    Returns:
        function: Обернутая функция с логированием исключений.
    """

    def __exception_logging(func):
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            """Создает запись лога с информацией о функции."""
            record = old_factory(*args, **kwargs)
            if hasattr(func, "__wrapped__"):
                record.funcName = func.__wrapped__.__name__
                record.filename = os.path.basename(
                    func.__wrapped__.__code__.co_filename
                )
                record.lineno = func.__wrapped__.__code__.co_firstlineno
            else:
                record.funcName = func.__name__
                record.filename = os.path.basename(func.__code__.co_filename)
                record.lineno = func.__code__.co_firstlineno
            return record

        @wraps(func)
        def wrapper(*args, **kwargs):
            """Обертка для функции с обработкой исключений."""
            try:
                result = func(*args, **kwargs)
            except custom_exception as e:
                logging.setLogRecordFactory(record_factory)
                signature = get_args_dict(func, args, kwargs)
                logger.debug(f"function {func.__name__} called with args {signature}")
                logger.exception(f"{message}\nError: {e}")
                logging.setLogRecordFactory(old_factory)
                if not ignore_raise:
                    raise
            else:
                return result

        return wrapper

    return __exception_logging


def redis_exceptor(func):
    """Декоратор для обработки исключений при работе с Redis.

    Args:
        func (function): Функция, которая будет обернута для обработки исключений.

    Returns:
        function: Обернутая асинхронная функция с обработкой исключений Redis.
    """

    @wraps(func)
    async def wrapper(pipeline: Pipeline):
        """Обертка для функции с обработкой исключений Redis."""
        try:
            logQuery = str(getattr(pipeline, "command_stack", ""))

            result = await func(pipeline)
            return result

        except rexc.AuthenticationError:
            rLogger.exception(
                f"Ошибка аутентификации при подключении к Redis :: {logQuery}"
            )
            raise DatabaseError
        except rexc.ConnectionError:
            rLogger.exception(f"Ошибка подключения к Redis :: {logQuery}")
            raise DatabaseError
        except rexc.TimeoutError:
            rLogger.exception(
                f"Превышено время ожидания при работе с Redis :: {logQuery}"
            )
            raise DatabaseError
        except IndexError:
            rLogger.exception("Command Stack is empty")
            raise DatabaseError
        except rexc.RedisError:
            rLogger.exception(f"Произошла неизвестная ошибка c Redis :: {logQuery}")
            raise DatabaseError

    return wrapper


def bot_except(func):
    """Декоратор для логирования исключений, возникающих в асинхронных функциях."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)

        except TelegramNetworkError as e:
            logger.warning(e.args[0])
        except AiogramError:
            logger.exception("Ошибка Aiogram API")
            raise
        except Exception:
            logger.exception("Неизвестная ошибка")
            raise
        else:
            return result

    return wrapper
