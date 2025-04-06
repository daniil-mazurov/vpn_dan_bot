import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import text
from core.config import settings
from db import utils
from db.models.enums import UserActivity
from db.models.wg_config import WgConfig
from server.pages.auth import User
from src.core import exceptions as exc
from src.core.path import PATH
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
        user_data = (await utils.get_all_userdata(user.user_id)).model_dump(mode="json")

        server_status = await WgServerTools().get_server_status()

    except exc.DatabaseError:
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

        # for transaction in user_data.get("transactions"):
        #     # TODO transaction_id

        # transaction["date"] = transaction["date"].date()
        # transaction["amount"] = round(transaction["amount"], 2)

        return templates.TemplateResponse(
            "profile.html",
            {
                "request": request,
                "user": user_data,
                "avatar": "".join(
                    [word[0] for word in user_data["telegram_name"].split()]
                ).upper(),
                "rate": text.rates.get(user_data["stage"], "Не выбран"),
                "rate_cost": round(user_data["stage"] * settings.cost, 2),
                "configsData": user_data["configs"],
                "server": server_status,
                "transactions": sorted(
                    user_data["transactions"], key=lambda x: x["date"], reverse=True
                ),
                "notifications": {
                    "data": sorted(
                        user_data["notifications"], key=lambda x: x["id"], reverse=True
                    ),
                    "len": len(user_data["notifications"]),
                },
            },
        )


class CloseNotificationRequest(BaseModel):
    id: int


@router.post("/close_notification")
async def close_notification(
    request: CloseNotificationRequest,
    user: Annotated[User, Depends(User.from_request)],
):
    try:
        notification_id = request.id  # Получаем ID уведомления
        await utils.remove_notification(notification_id)
    except exc.DatabaseError:
        logger.exception(
            f"Ошибка БД при удалении уведомления пользователя {user.user_id}"
        )
        return RedirectResponse(
            url="/vpn/500", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    except Exception:
        logger.exception(
            f"Неизвестная ошибка при удалении уведомления пользователя {user.user_id}"
        )
        return RedirectResponse(
            url="/vpn/500", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    else:
        return {"answer": "ok"}


class ResponseModel(BaseModel):
    success: bool
    message: str = None  # Optional error message


@router.post("/create")
async def create_config(
    response: Response,
    user: Annotated[User, Depends(User.from_request)],
):
    try:
        user_data = await utils.get_all_userdata(user.user_id)

        if user_data.active != UserActivity.active:
            raise exc.PayError

        elif len(user_data.configs) < settings.acceptable_config[user_data.stage]:
            wg = WgServerTools()
            conf = await wg.move_user(move="add", user_id=user.user_id)
            config: WgConfig = await utils.add_wg_config(conf, user_id=user.user_id)

        else:
            raise exc.StagePayError
    except exc.DatabaseError as e:
        logger.exception(
            f"Ошибка БД при создании конфигурации пользователя {user.user_id}"
        )

        return ResponseModel(success=False, message=str(e))
    except exc.WireguardError:
        logger.exception(
            f"Ошибка WireGuard сервера при создании конфигурации пользователя {user.user_id}"
        )
        return ResponseModel(success=False, message=text.WG_ERROR)

    except exc.StagePayError:
        return ResponseModel(
            success=False,
            message="Достигнуто максимальное количество конфигураций для данного тарифа.",
        )

    except exc.PayError:
        return ResponseModel(success=False, message=text.UNPAY)

    except Exception as e:
        logger.exception(
            f"Неизвестная ошибка при создании конфигурации пользователя {user.user_id}"
        )

        return ResponseModel(success=False, message=str(e))

    else:
        return ResponseModel(
            success=True, message=f"Конфигурация {config.name} успешно создана!"
        )
