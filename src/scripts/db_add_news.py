import asyncio
import logging
import logging.config
import os
import sys
from datetime import datetime

sys.path.insert(1, os.path.dirname(sys.path[0]))


from db.utils import add_news

logging.config.fileConfig("log.ini", disable_existing_loggers=False)
logger = logging.getLogger()

# Пример данных новостей
news_data = {
    "news_id": "news1",
    "date": datetime.today().date(),
    "title": "Запуск сервиса в тестовом режиме",
    "excerpt": "Уважаемый пользователь, сейчас наш сервис находится на стадии тестирования. Если вы столкнетесь с какой-либо проблемой в работе сервиса, пожалуйста воспользуйтесь командой /bug и сообщите нам о ней.",
    "content_title": "🚀 Первый запуск! Полет нормальный.",
    "content": """
    <p>Дорогие пользователи! Мы рады сообщить, что наш VPN сервис успешно запущен и сейчас работает в тестовом режиме! 🎉</p>
    <p>Мы стремимся предоставить вам надежное и безопасное соединение, и на этом этапе мы будем внимательно следить за работой сервиса, чтобы устранить любые возможные проблемы.</p>
    <p>Пожалуйста, делитесь своими впечатлениями и сообщайте о любых замеченных ошибках. Для этого воспользуйтесь <a href="/bot/bug/create">ссылкой</a> либо командой `<a href="https://t.me/vpn_dan_bot">/bug</a>` в нашем чат-боте. Ваши отзывы помогут нам улучшить наш сервис!</p>""",
}


if __name__ == "__main__":
    asyncio.run(add_news(news_data))
