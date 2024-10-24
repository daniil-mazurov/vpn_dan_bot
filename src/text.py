import os
import uuid
from dataclasses import dataclass

import aiofiles
import pyqrcode
from pytils.numeral import get_plural

from core.config import settings
from core.path import PATH
from db.models import UserActivity, UserData, WgConfig

me = {"я", "мои данные", "данные", "конфиги", "мои конфиги", "config", "конфигурации"}
yes = {"yes", "y", "da", "да"}
no = {"no", "n", "нет"}

only_admin = "Данный функционал предназначен для пользования администратором. Если вы администратор, а мы не знаем об этом, отправьте боту секретный пароль."

DB_ERROR = "Ошибка подключения к БД. Обратитесь к администратору."
WG_ERROR = "Ошибка подключения к серверу wireguard. Обратитесь к администратору."
YOO_ERROR = "Ошибка подключения к серверу yoomoney. Попробуйте еще раз позже"
UNPAY = "Функционал создания конфигураций заблокирован. Действующие конфигурации заблокированы. Для разблокировки оплатите подписку."

rates = {0.3: "Пробный", 1: "Базовый", 2.5: "Расширенный", 5: "Люкс"}


@dataclass
class AccountStatuses:
    freezed = "Заморожен"
    admin = "Администратор"
    user = "Пользовательский"
    deleted = "Удален"
    banned = "Забанен"


def get_account_status(user_data: UserData):
    if user_data.active == UserActivity.freezed:
        return AccountStatuses.freezed
    elif user_data.admin:
        return AccountStatuses.admin
    else:
        return AccountStatuses.user


def get_sub_status(user_data: UserData):
    if user_data.active == UserActivity.active:
        return f"Активна | {rates.get(user_data.stage,'Неопознанный')} Тариф"
    elif user_data.active == UserActivity.inactive:
        return "Неактивна"
    else:
        return ""


def get_config_data(user_config: WgConfig):
    return f"""[Interface]
PrivateKey = {user_config.user_private_key}
Address = {user_config.address}
DNS = {user_config.dns}
[Peer]
PublicKey = {settings.WG_SERVER_KEY}
AllowedIPs = {user_config.allowed_ips}
Endpoint = {user_config.endpoint_ip}:{user_config.endpoint_port}
PersistentKeepalive = 25
"""


async def create_config_file(config: str):
    path = os.path.join(PATH, "tmp", f"{uuid.uuid3(uuid.NAMESPACE_DNS, config)}.conf")

    async with aiofiles.open(path, "w") as file:
        await file.write(config)

    return path


def create_config_qr(config: str):
    path = os.path.join(PATH, "tmp", f"{uuid.uuid3(uuid.NAMESPACE_DNS, config)}.png")

    qr = pyqrcode.create(config)
    qr.png(path, scale=8)

    return path


def get_end_sub(user_data: UserData):
    try:
        end = round(user_data.fbalance / (user_data.stage * settings.cost))
    except ZeroDivisionError:
        end = 0
    else:
        if end < 0:
            end = 0

    return end


def get_rate_descr(rate: int):
    general_1 = "\n<b>‼️ (Плата взимается ежедневно!)</b>"
    general_2 = "\n\n❗️ (Одна конфигурация может быть подключена к нескольким устройствам, однако такие подключения не могут быть одновременными, поэтому рекомендуется создавать по одной конфигурации на каждое устройство)"

    match rate:
        case 0:
            descr = "<b>Тариф: Нулевой</b>" "\nНе подключен никакой тариф" + general_2
        case 0.3:
            descr = (
                "<b>Тариф: Пробный</b>\n"
                "\n❗️ Может быть подключен <b>единоразово</b>"
                "\nПодключение другого тарифа лишает пользователя возможности подключить этот тариф"
                "\n\n‼️ Время действия пробного периода <b>7 дней</b>"
                "\n\n✅ Позволяет опробовать функционал подключения к VPN сервису"
                "\n✅ Доступно создание 1 конфигурации (1 устройство)" + general_2
            )
        case 1:
            descr = (
                "<b>Тариф: ⭐️Базовый⭐️</b>\n"
                "\n✅ Позволяет получить доступ к базовому функционалу VPN сервиса"
                "\n✅ Доступно создание 3 конфигураций (3 устройства)"
                + general_2
                + f"\n\n‼️ Актуальная стоимость тарифа: <b>{get_plural(settings.cost * rate, 'рубль, рубля, рублей')} в день</b>."
                + general_1
            )
        case 2.5:
            descr = (
                "<b>Тариф: 🌟Расширенный🌟</b>\n"
                "\n✅ Позволяет получить доступ к расширенному функционалу VPN сервиса"
                "\n✅ Доступны различные инструменты анализа работы VPN сервиса"
                "\n✅ Возможность отключать ненужные уведомления"
                "\n✅ Доступно создание 8 конфигураций (8 устройств)"
                + general_2
                + f"\n\n‼️ Актуальная стоимость тарифа: <b>{get_plural(settings.cost * rate, 'рубль, рубля, рублей')} в день</b>. "
                + general_1
            )
        case 5:
            descr = (
                "<b>Тариф: 💰Люкс💰</b>\n"
                "\n✅ Позволяет получить доступ к максимально доступному функционалу VPN сервиса"
                "\n✅ Доступны различные инструменты анализа работы VPN сервиса"
                "\n✅ Возможность отключать ненужные уведомления"
                "\n✅ Круглосуточный доступ к техподдержке сервиса (Поможет и расскажет как все настроить или починить)"
                "\n✅ Только обладатели тарифа Люкс могут подать заявку на получение статуса Администратор"
                "\n✅ Доступно создание 15 конфигураций (15 устройств)"
                + general_2
                + f"\n\n‼️ Актуальная стоимость тарифа: <b>{get_plural(settings.cost * rate, 'рубль, рубля, рублей')} в день</b>. "
                + general_1
            )
    return descr
