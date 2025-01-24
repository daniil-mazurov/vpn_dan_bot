"""Все кнопки и клавиатуры для хендлеров"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from pytils.numeral import get_plural

from core.config import settings
from db.models import UserActivity, UserData
from text import rates

static_join_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Присоединиться!", callback_data="start_app")]
    ]
)
"""Клавиатура для кнопки "Присоединиться!".

    Используется для приглашения пользователя присоединиться к приложению.
"""

static_wg_url = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Скачать WireGuard", url="https://www.wireguard.com/install/"
            )
        ]
    ]
)
"""Клавиатура с кнопкой для скачивания WireGuard.

    Предоставляет пользователю ссылку на установку WireGuard.
"""

static_wg_platform_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Windows", callback_data="wg_help_info_Windows_start"
            ),
            InlineKeyboardButton(
                text="Linux", callback_data="wg_help_info_Linux_start"
            ),
            InlineKeyboardButton(
                text="macOS", callback_data="wg_help_info_macOS_start"
            ),
        ],
        [
            InlineKeyboardButton(
                text="Android", callback_data="wg_help_info_Android_start"
            ),
            InlineKeyboardButton(text="iOS", callback_data="wg_help_info_iOS_start"),
        ],
    ]
)
"""Клавиатура для выбора платформы WireGuard.

    Позволяет пользователю выбрать операционную систему для получения
    соответствующей информации по настройке WireGuard.
"""

static_reg_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Зарегистироваться", callback_data="register_user")]
    ]
)
"""Клавиатура с кнопкой регистрации.

    Используется для начала процесса регистрации нового пользователя.
"""

static_pay_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Купить подписку", callback_data="user_payment")]
    ]
)
"""Клавиатура с кнопкой для покупки подписки.

    Позволяет пользователю перейти к процессу покупки подписки.
"""

static_start_button = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Перезагрузка"),
            KeyboardButton(text="Статус"),
        ],
        [
            KeyboardButton(text="Подключения"),
            KeyboardButton(text="Подписка"),
        ],
        [
            KeyboardButton(text="Помощь"),
            KeyboardButton(text="Чат"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие или введите команду",
)
"""Клавиатура для основных действий пользователя.

    Предоставляет пользователю выбор действий, таких как перезагрузка,
    проверка статуса, подключений, подписки и получения помощи.
"""

static_support_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Доложить о проблеме", callback_data="call_support")]
    ]
)
"""Клавиатура с кнопкой для обращения в службу поддержки.

    Позволяет пользователю сообщить о проблеме или запросить помощь.
"""

static_balance_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Пополнить баланс", callback_data="top_up_balance")]
    ]
)
"""Клавиатура с кнопкой для пополнения баланса.

    Позволяет пользователю перейти к процессу пополнения своего баланса.
"""

why_freezed_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Почему моя конфигурация заморожена?", callback_data="freeze_info"
            )
        ]
    ]
)
"""Клавиатура с кнопкой для получения информации о замороженной конфигурации.

    Позволяет пользователю узнать причины, по которым его конфигурация заморожена.
"""

freeze_user_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Заморозить аккаунт", callback_data="freeze_account"
            )
        ]
    ]
)
"""Клавиатура с кнопкой для заморозки аккаунта.

    Позволяет пользователю инициировать процесс заморозки своего аккаунта.
"""

static_history_button = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Пополнения", callback_data="transact_history_in"
            ),
            InlineKeyboardButton(text="Снятия", callback_data="transact_history_out"),
        ],
    ]
)
"""Клавиатура для отображения истории транзакций.

    Позволяет пользователю просмотреть историю пополнений и снятий средств.
"""


def get_help_menu(name, user_id):
    """Создает меню помощи для пользователя.

    Args:
        name (str): Имя пользователя.
        user_id (int): ID пользователя.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками помощи.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Что это за сервис?", callback_data="bot_info")],
            [
                InlineKeyboardButton(
                    text="Я первый раз. Что мне делать?",
                    callback_data="first_help_info_start",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Как мне настроить WireGuard?", callback_data="wg_help_info"
                )
            ],
            [
                InlineKeyboardButton(
                    text="У меня тормозит или не работает VPN",
                    callback_data="error_help_info_start",
                )
            ],
            [InlineKeyboardButton(text="Команды", callback_data="cmd_help_info")],
            [
                InlineKeyboardButton(
                    text="Задать свой вопрос",
                    url=f"{settings.subserver_url}bot/bug/create?name={name}&telegram_id={user_id}",
                )
            ],
        ]
    )


def get_help_book_keyboard(pages: list, page: int, prefix: str):
    """Создает клавиатуру для навигации по страницам помощи.

    Args:
        pages (list): Список страниц.
        page (int): Номер текущей страницы.
        prefix (str): Префикс для callback_data.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками навигации.
    """
    prev_page = page - 1
    next_page = page + 1
    if page == 0:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Следующий шаг",
                        callback_data=f"{prefix}_{next_page}",
                    )
                ]
            ]
        )
    if page == len(pages) - 1:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Предыдущий шаг",
                        callback_data=f"{prefix}_{prev_page}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Покажи весь алгоритм", callback_data=f"{prefix}_all"
                    )
                ],
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Предыдущий шаг", callback_data=f"{prefix}_{prev_page}"
                ),
                InlineKeyboardButton(
                    text="Следующий шаг", callback_data=f"{prefix}_{next_page}"
                ),
            ],
        ]
    )


def get_account_keyboard(user_data: UserData, extended=False):
    """Создает клавиатуру для управления аккаунтом пользователя.

    Args:
        user_data (UserData): Данные пользователя.
        extended (bool, optional): Если True, добавляются дополнительные кнопки.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками управления аккаунтом.
    """
    buttons = []
    match getattr(user_data, "active", None):
        case UserActivity.active | UserActivity.inactive:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="❄️ Заморозить аккаунт", callback_data="freeze_account_info"
                    )
                ]
            )
        case UserActivity.freezed:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="🔥 Разморозить аккаунт", callback_data="recover_account"
                    )
                ]
            )
        case UserActivity.banned:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="Подать заявку на разбан",
                        url=f"{settings.subserver_url}bot/bug/create?name={user_data.telegram_name}&telegram_id={user_data.telegram_id}",
                    )
                ]
            )
            return InlineKeyboardMarkup(inline_keyboard=buttons)
        case _:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="Зарегистироваться", callback_data="register_user"
                    )
                ]
            )
            return InlineKeyboardMarkup(inline_keyboard=buttons)
    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="📂 Мои конфигурации", callback_data="user_configurations"
                )
            ],
            [InlineKeyboardButton(text="🤩 Подписка", callback_data="user_payment")],
            [InlineKeyboardButton(text="🆘 Помощь", callback_data="main_help")],
        ]
    )
    if not extended:
        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text="⏬ Инструменты", callback_data="extra_function_open"
                    )
                ]
            ]
        )
    else:
        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text="⏫ Инструменты", callback_data="extra_function_close"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="💬 Наш чат", callback_data="invite_to_chat"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🆔 Мой ID", callback_data="user_id_info"
                    ),
                    InlineKeyboardButton(
                        text="🔊 Unmute" if user_data.mute else "🔇 Mute",
                        callback_data="user_mute_toggle",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔍 Сервер", callback_data="server_status"
                    ),
                    InlineKeyboardButton(
                        text="⚡️ Скорость VPN", callback_data="server_speed"
                    ),
                ],
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_config_keyboard():
    """Создает клавиатуру для создания конфигурации.

    Returns:
        tuple: Кортеж из клавиатур для создания конфигурации и выбора формата.
    """
    buttons = []
    cfgs = []
    cfgs.append(
        [
            InlineKeyboardButton(text="TEXT", callback_data="create_conf_text"),
            InlineKeyboardButton(text="QR", callback_data="create_conf_qr"),
            InlineKeyboardButton(text="FILE", callback_data="create_conf_file"),
            InlineKeyboardButton(text="🚮", callback_data="remove_config_confirm"),
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text="Создать конфигурацию", callback_data="create_configuration"
            ),
        ]
    )
    return (
        InlineKeyboardMarkup(inline_keyboard=buttons),
        InlineKeyboardMarkup(inline_keyboard=cfgs),
    )


def get_subscr_buttons(user_data: UserData, force_rates=False):
    """Создает клавиатуру для выбора подписки.

    Args:
        user_data (UserData): Данные пользователя.
        force_rates (bool, optional): Если True, принудительно отображает тарифы.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками подписки.
    """
    buttons = []
    my_rate = rates.get(user_data.stage, None)
    if my_rate or force_rates:
        for key, rate in rates.items():
            if rate == my_rate:
                prefix = "✅ "
            elif not user_data.free and key == 0.3:
                prefix = "❌ "
            else:
                prefix = ""
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"{prefix}{rate} тариф", callback_data=f"rate_info_{key}"
                    )
                ]
            )
        if not force_rates:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text="Пополнить баланс", callback_data="top_up_balance"
                    ),
                    InlineKeyboardButton(
                        text="История операций", callback_data="transact_history"
                    ),
                ],
            )
    else:
        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text="Выбрать тариф", callback_data="change_rate"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Пополнить баланс", callback_data="top_up_balance"
                    ),
                    InlineKeyboardButton(
                        text="История операций", callback_data="transact_history"
                    ),
                ],
            ]
        )
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_rate_button(rate: int):
    """Создает кнопку для выбора тарифа.

    Args:
        rate (int): Значение тарифа.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой выбора тарифа.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Выбрать этот тариф", callback_data=f"accept_rate_{rate}"
                )
            ]
        ]
    )


def get_pay_keyboard():
    """Создает клавиатуру для выбора суммы оплаты.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для оплаты.
    """
    buttons = [
        [
            InlineKeyboardButton(text="100", callback_data="pay_sub_100"),
            InlineKeyboardButton(text="250", callback_data="pay_sub_250"),
            InlineKeyboardButton(text="500", callback_data="pay_sub_500"),
            InlineKeyboardButton(text="1000", callback_data="pay_sub_1000"),
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_bug_report_url(name, user_id):
    """Создает кнопку для заполнения формы обращения.

    Args:
        name (str): Имя пользователя.
        user_id (int): ID пользователя.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой для заполнения формы обращения.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Заполнить форму обращения",
                    url=f"{settings.subserver_url}bot/bug/create?name={name}&telegram_id={user_id}",
                )
            ]
        ]
    )


def get_pay_url(sum, url):
    """Создает кнопку для пополнения баланса.

    Args:
        sum (float): Сумма пополнения.
        url (str): URL для пополнения.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой для пополнения.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Пополнить на {get_plural(sum, 'рубль, рубля, рублей')}",
                    url=url,
                )
            ]
        ]
    )


def get_chat_button(url):
    """Создает кнопку для получения доступа в чат.

    Args:
        url (str): URL для доступа в чат.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой для доступа в чат.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌟Получить доступ в чат",
                    url=url,
                )
            ]
        ]
    )


def remove_config():
    buttons = [
        [
            InlineKeyboardButton(text="Удалить", callback_data="remove_config"),
            InlineKeyboardButton(text="Отмена", callback_data="remove_config_cancel"),
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
