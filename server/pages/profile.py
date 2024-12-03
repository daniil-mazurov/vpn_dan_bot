import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
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
        user_data = (await utils.get_all_userdata(user.user_id)).model_dump()

        server_status = await WgServerTools().get_server_status()

    except DatabaseError:
        logger.exception(f"Ошибка БД при загрузке профиля пользователя {user.user_id}")
        return RedirectResponse(
            url="/vpn/500", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    except Exception:
        logger.exception(
            f"Неизвестная ошибка при загрузке профиля пользователя {user.user_id}"
        )
        return RedirectResponse(
            url="/vpn/500", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    else:
        for config in user_data.get("configs"):
            config["PersistentKeepalive"] = 25
            config["PublicKey"] = settings.WG_SERVER_KEY

        for transaction in user_data.get("transactions"):
            # TODO transaction_id

            transaction["date"] = transaction["date"].date()
            transaction["amount"] = round(transaction["amount"], 2)

        return templates.TemplateResponse(
            "profile.html",
            {
                "request": request,
                "user": user_data,
                "avatar": "".join(
                    [word[0] for word in user_data["telegram_name"].split()]
                ).upper(),
                "rate": rates.get(user_data["stage"], "Не выбран"),
                "rate_cost": round(user_data["stage"] * settings.cost, 2),
                "configsData": user_data["configs"],
                "server": server_status,
                "transactions": user_data["transactions"],
                "notifications": {
                    "data": user_data["notifications"],
                    "len": len(user_data["notifications"]),
                },
            },
        )
