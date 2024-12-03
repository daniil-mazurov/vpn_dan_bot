from datetime import datetime, timezone
import logging
import os
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from db import models as mod
from db import utils
from server.pages.auth import User
from src.core.exceptions import DatabaseError
from src.core.path import PATH
from text import rates, reverse_rates

router = APIRouter()
logger = logging.getLogger()
queue = logging.getLogger("queue")


templates = Jinja2Templates(directory=os.path.join(PATH, "server", "templates"))


@router.get("", response_class=HTMLResponse)
async def pricing_page(
    request: Request,
    user: Annotated[User, Depends(User.from_request_opt)],
):
    return templates.TemplateResponse(
        "pricing.html",
        {
            "request": request,
            "name": "Профиль" if user else "Войти",
        },
    )


@router.post("/change_rate/{rate}")
async def set_new_rate(
    response: Response,
    rate: Literal["free", "base", "advanced", "luxury"],
    user: Annotated[User, Depends(User.from_request)],
):
    try:
        user_data = await utils.get_user_with_configs(user.user_id)
        rate_id = reverse_rates.get(rate)

        if not user_data:
            return {"message": "Профиль не найден"}
        elif user_data.stage == rate_id:
            await utils.add_notification(
                mod.Notifications.ValidationSchema(
                    user_id=user.user_id,
                    type=mod.NotificationType.error,
                    message="У вас уже подключен этот тариф",
                    date=datetime.now(timezone.utc),
                )
            )

            return
        elif user_data.stage == 0.3:
            return {
                "message": "Дождитесь окончания пробного периода или пополните баланс"
            }
        elif rate_id == 0.3:
            if user_data.free:
                await utils.update_rate_user(
                    user_data.telegram_id, stage=rate_id, trial=True
                )
            else:
                return {
                    "message": "К сожалению вы исчерпали возможность подключения пробного периода"
                }
        elif user_data.stage > rate_id:
            await utils.update_rate_user(
                user_data.telegram_id, stage=rate_id, tax=user_data.stage * 10
            )
        else:
            await utils.update_rate_user(user_data.telegram_id, stage=rate_id)
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
        logger.info(f"Изменение тарифа на {rates[rate_id]} успешно!")
        return {"message": f"Изменение тарифа на {rates[rate_id]} успешно!"}
