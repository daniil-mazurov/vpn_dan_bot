import logging
import os
from datetime import datetime, timedelta
from typing import Dict

import jwt
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import select
from typing_extensions import Self

from core.config import settings
from server.err import RequiresLoginException
from src.app import models as mod
from src.core.path import PATH
from src.db.database import execute_query
from src.db.utils.redis import CashManager

router = APIRouter()
logger = logging.getLogger()
queue = logging.getLogger("queue")

templates = Jinja2Templates(directory=os.path.join(PATH, "server", "templates"))


# @dataclass
class User(BaseModel):
    user_id: int

    def auth_user(self) -> Dict[str, str]:
        payload = {"user_id": self.user_id, "exp": datetime.now() + timedelta(days=30)}
        token = jwt.encode(
            payload,
            settings.JWT_SECRET.get_secret_value(),
            algorithm=settings.ALGORITHM,
        )

        return token

    @classmethod
    def decodeJWT(cls, token: str) -> dict:
        decoded_token = jwt.decode(
            token,
            settings.JWT_SECRET.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )

        return (
            decoded_token
            if datetime.fromtimestamp(decoded_token["exp"]) > datetime.now()
            else None
        )

    @classmethod
    def from_request(cls, request: Request) -> Self:
        user = cls.from_request_opt(request)
        if user is None:
            raise RequiresLoginException
        else:
            return user

    @classmethod
    def from_request_opt(cls, request: Request) -> Self | None:
        try:
            token = request.cookies.get("users_access_token")
            payload = cls.decodeJWT(token)

        except (jwt.DecodeError, jwt.ExpiredSignatureError):
            return None

        else:
            # existing token might not have 'exp' field
            payload.pop("exp", None)
            return cls(**payload)


@router.get("/login", response_class=HTMLResponse)
async def auth_page(request: Request, redirected: str):
    return templates.TemplateResponse(
        "auth.html",
        {"request": request, "redirected": redirected},
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers={"Location": f"/vpn/auth/login?redirected={redirected}"},
    )


@router.get("/redirect", response_class=HTMLResponse)
async def auth_success(redirected: str):
    return RedirectResponse(url=redirected)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="users_access_token")
    return {"message": "Пользователь успешно вышел из системы"}


class IDRequest(BaseModel):
    __tablename__ = "userdata"

    telegram_id: int


class CodeRequest(BaseModel):
    __tablename__ = "userdata"

    code: int


class AuthRequest(IDRequest, CodeRequest): ...


@router.post("/send_code")
async def send_code(request: IDRequest):
    try:
        telegram_id = request.telegram_id

        query = select(mod.UserData).where(mod.UserData.telegram_id == telegram_id)
        raw_tg_user: mod.UserData = (await execute_query(query)).scalar_one_or_none()

        assert raw_tg_user

        logger.info(f"Sending code to Telegram ID: {telegram_id}")

        queue.info(
            "Отправка кода для авторизации",
            extra={
                "type": "CODE",
                "user_id": request.telegram_id,
                "label": None,
                "amount": None,
            },
        )

        return {"message": "Code sent successfully", "telegram_id": telegram_id}

    except AssertionError:
        logger.warning(
            f"Telegram ID: {telegram_id} не верный либо пользователь не доступен"
        )
        raise HTTPException(status_code=500)
    except Exception as e:
        logger.exception(f"Ошибка отправки временного кода пользователя {telegram_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify_code")
async def verify_code(response: Response, request: AuthRequest):
    try:
        telegram_id = request.telegram_id

        result: list[CodeRequest] = await CashManager(CodeRequest).get(
            {f"authcode:{telegram_id}": ...}
        )

        assert request.code == result[0].code

        user = User(user_id=telegram_id)
        access_token = user.auth_user()
        response.set_cookie(key="users_access_token", value=access_token, httponly=True)

        logger.info(f"Auth the user: {telegram_id} success")

        return {"message": "Code verify successfully", "telegram_id": telegram_id}

    except AssertionError:
        logger.warning(f"Неправильно введен код пользователем: {telegram_id}")
        raise HTTPException(status_code=500)
    except Exception as e:
        logger.exception(
            f"Ошибка верификации временного кода пользователя {telegram_id}"
        )
        raise HTTPException(status_code=500, detail=str(e))
