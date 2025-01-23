"""Функционал для работы с БД. Резервирование"""

import asyncio
import logging
import os
from datetime import datetime, timedelta

from pandas import DataFrame, ExcelWriter
from sqlalchemy import select

from core.config import settings
from core.exceptions import BackupError, DumpError
from core.path import PATH
from db.database import execute_query
from db.models import TABLES_SCHEMA, Base

logger = logging.getLogger()


async def async_backup():
    """Создает резервную копию базы данных в формате Excel.

    Функция извлекает данные из всех таблиц, определенных в TABLES_SCHEMA,
    и сохраняет их в файл Excel. Даты в столбцах преобразуются в локальное время.

    Returns:
        str: Путь к созданному файлу резервной копии.

    Raises:
        BackupError: Если произошла ошибка при создании резервной копии.
    """
    filename = os.path.join(
        PATH,
        "src",
        "db",
        "backups",
        f"backup_{datetime.today().strftime('%d_%m_%Y-%H_%M')}.xlsx",
    )
    with ExcelWriter(filename, engine="openpyxl", mode="w") as writer:
        try:
            for model in TABLES_SCHEMA.values():
                if model.__bases__[0] is Base:
                    query = select(model).order_by(model.id)
                    res = await execute_query(query)

                    df = DataFrame(
                        data=[line.__udict__ for line in res.scalars().all()]
                    )

                    date_columns = df.select_dtypes(
                        include=["datetime64[ns, UTC]"]
                    ).columns
                    for date_column in date_columns:
                        df[date_column] = df[date_column].dt.tz_localize(None)
                        df[date_column] = df[date_column] + timedelta(hours=3)

                    df.to_excel(writer, sheet_name=model.__tablename__, index=False)
        except Exception:
            logger.exception("Ошибка создания дампа БД")
            raise BackupError
        else:
            return filename


async def dump(regular=False):
    """Создает дамп базы данных в формате SQL.

    Функция выполняет команду pg_dump для создания дампа базы данных.
    Дамп сохраняется в файл с указанием, является ли он регулярным.
    (НЕ РАБОТАЕТ НА WINDOWS - я хз как передавать пароль утилите pg_dump)

    Args:
        regular (bool): Указывает, является ли дамп регулярным. По умолчанию False.

    Returns:
        None

    Raises:
        DumpError: Если произошла ошибка при создании дампа.
    """
    filename = os.path.join(
        PATH,
        "src",
        "db",
        "dumps",
        f"{'regular_' if regular else ''}dump_{datetime.today().strftime('%d_%m_%Y-%H_%M')}.sql",
    )

    cmd = (
        f"PGPASSWORD={settings.DB_PASS.get_secret_value()} "
        f"pg_dump -U {settings.DB_USER} {settings.DB_NAME} "
        f"-p {settings.DB_PORT} -h {settings.DB_HOST} > {filename}"
    )

    logger.info("Создание дампа БД")

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        logger.info(f"pg_dump exited with {proc.returncode}")

        if proc.returncode != 0:
            # Попробуйте декодировать с игнорированием ошибок
            error_message = stderr.decode("utf-8", errors="ignore")
            logger.error(f"Ошибка создания дампа БД: {error_message}")
            raise DumpError(error_message)
        else:
            logger.info("Дамп БД успешно создан", extra={"dumpname": filename})

    except Exception as e:
        logger.exception("Произошла ошибка при создании дампа БД")
        raise DumpError(str(e))
