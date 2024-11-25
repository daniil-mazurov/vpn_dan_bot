"""Создание регулярного дампа"""

import logging
from datetime import datetime
from pathlib import Path

from core.config import settings
from core.err import log_cash_error
from core.path import PATH
from db.utils import dump

logger = logging.getLogger("apscheduler")
logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)


async def regular_dump():
    """Создает регулярный дамп базы данных и управляет старыми дампами.

    Эта функция выполняет создание дампа базы данных с помощью функции `dump`.
    Затем она проверяет, превышает ли количество дампов максимальное количество,
    установленное в конфигурации. Если да, то удаляет старые дампы.

    Raises:
        DumpError: Если произошла ошибка при создании дампа базы данных.
    """
    try:
        await dump(regular=True)

        folder_path = Path(PATH) / "src" / "db" / "dumps"

        dumps = [
            file
            for file in folder_path.iterdir()
            if file.is_file() and "regular" in file.name
        ]

        if len(dumps) > settings.max_dumps:
            dumps = sorted(
                dumps,
                key=lambda file: datetime.strptime(
                    file.name.split("dump")[-1].strip("_.sql"), "%d_%m_%Y-%H_%M"
                ),
            )
            for _dump in dumps[: len(dumps) - settings.max_dumps]:
                _dump.unlink()

    except Exception as e:
        if log_cash_error(e):
            logger.exception("Ошибка создания регулярного дампа")
