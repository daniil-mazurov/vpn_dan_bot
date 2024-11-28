import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core.config import settings
from db import utils
from server.pages.auth import User
from src.core.exceptions import DatabaseError
from src.core.path import PATH
from text import rates
from wg.utils import WgServerTools

router = APIRouter()
logger = logging.getLogger()
queue = logging.getLogger("queue")


templates = Jinja2Templates(directory=os.path.join(PATH, "server", "templates"))


@router.get("", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    user: Annotated[User, Depends(User.from_request)],
):
    try:
        user_data = await utils.get_user_with_configs(user.user_id)

        raw_transactions = await utils.get_user_transactions(user.user_id)

        server_status = await WgServerTools().get_server_status()

    except DatabaseError:
        logger.exception(f"Ошибка БД при загрузке профиля пользователя {user.user_id}")
        return templates.TemplateResponse("500.html", {"request": request})

    except Exception:
        logger.exception(
            f"Неизвестная ошибка при загрузке профиля пользователя {user.user_id}"
        )
        return templates.TemplateResponse("500.html", {"request": request})

    else:
        configs = []
        for config in user_data.configs:
            config = config.__ustr_dict__
            config["PersistentKeepalive"] = 25
            config["PublicKey"] = settings.WG_SERVER_KEY

            configs.append(config)

        transactions = []
        for transaction in raw_transactions:
            # TODO transaction_id

            transaction.date = transaction.date.date()
            transaction.amount = round(transaction.amount, 2)
            transaction = transaction.__udict__
            transactions.append(transaction)

        return templates.TemplateResponse(
            "profile.html",
            {
                "request": request,
                "user": user_data.__ustr_dict__,
                "avatar": "".join(
                    [word[0] for word in user_data.telegram_name.split()]
                ).upper(),
                "rate": rates.get(user_data.stage, "Не выбран"),
                "rate_cost": round(user_data.stage * settings.cost, 2),
                "configsData": configs,
                "server": server_status,
                "transactions": transactions,
            },
        )
