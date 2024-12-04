import logging
import os
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.config import settings
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
    rates_costs = {
        name: {
            "day": round(multiplier * settings.cost, 2),
            "month": round(multiplier * settings.cost * 30),
        }
        for multiplier, name in rates.items()
    }
    return templates.TemplateResponse(
        "pricing.html",
        {
            "request": request,
            "name": "Профиль" if user else "Войти",
            "rates_costs": rates_costs,
        },
    )


@router.post("/change_rate/{rate}")
async def set_new_rate(
    rate: Literal["free", "base", "advanced", "luxury"],
    user: Annotated[User, Depends(User.from_request)],
):
    try:
        user_data = await utils.get_user_with_configs(user.user_id)
        rate_id = reverse_rates.get(rate)

        if not user_data:
            return
        elif user_data.stage == rate_id:
            await utils.add_notification(
                mod.Notifications.ValidationSchema(
                    user_id=user.user_id,
                    type=mod.NotificationType.error,
                    message=f"У вас уже подключен тариф '{rates[rate_id]}'",
                    date=datetime.now().ctime(),
                )
            )

            return
        elif user_data.stage == 0.3:
            await utils.add_notification(
                mod.Notifications.ValidationSchema(
                    user_id=user.user_id,
                    type=mod.NotificationType.error,
                    message="Дождитесь окончания пробного периода или пополните баланс",
                    date=datetime.now().ctime(),
                )
            )

            return
        elif rate_id == 0.3:
            if user_data.free:
                await utils.update_rate_user(
                    user_data.telegram_id, stage=rate_id, trial=True
                )
            else:
                await utils.add_notification(
                    mod.Notifications.ValidationSchema(
                        user_id=user.user_id,
                        type=mod.NotificationType.error,
                        message="К сожалению вы исчерпали возможность подключения пробного периода",
                        date=datetime.now().ctime(),
                    )
                )

                return
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

        await utils.add_notification(
            mod.Notifications.ValidationSchema(
                user_id=user.user_id,
                type=mod.NotificationType.success,
                message=f"Изменение тарифа на {rates[rate_id]} успешно!",
                date=datetime.now().ctime(),
            )
        )
