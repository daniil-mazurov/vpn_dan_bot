import logging
import os
from functools import wraps

from redis import exceptions as rexc
from redis.asyncio.client import Pipeline

from core.exceptions import DatabaseError

logger = logging.getLogger()
rlogger = logging.getLogger("redis")


def _get_args_dict(fn, args, kwargs):
    args_names = fn.__code__.co_varnames[: fn.__code__.co_argcount]
    return {**dict(zip(args_names, args)), **kwargs}


def exception_logging(
    ignore_raise=False,
    custom_exception=Exception,
    message="Something went wrong",
):
    """Логирование возникающих в функции исключений (NOT FOR ASYNC)

    Args:
        ignore_raise (bool, optional): Прерывать ли ход действия программы? Defaults to False.
    """

    def __exception_logging(func):
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
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
            try:
                result = func(*args, **kwargs)
            except custom_exception as e:
                logging.setLogRecordFactory(record_factory)

                signature = _get_args_dict(func, args, kwargs)
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
    @wraps(func)
    async def wrapper(pipeline: Pipeline):
        try:
            logquery = str(getattr(pipeline, "command_stack", ""))

            result = await func(pipeline)
            return result

        except rexc.AuthenticationError:
            rlogger.exception(
                f"Ошибка аутентификации при подключении к Redis :: {logquery}"
            )
            raise DatabaseError
        except rexc.ConnectionError:
            rlogger.exception(f"Ошибка подключения к Redis :: {logquery}")
            raise DatabaseError
        except rexc.TimeoutError:
            rlogger.exception(
                f"Превышено время ожидания при работе с Redis :: {logquery}"
            )
            raise DatabaseError
        except IndexError:
            rlogger.exception("Command Stack is empty")
            raise DatabaseError
        except rexc.RedisError:
            rlogger.exception(f"Произошла неизвестная ошибка c Redis :: {logquery}")
            raise DatabaseError

    return wrapper
