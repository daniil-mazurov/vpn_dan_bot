import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import select

from server.pages.auth import User
from src.app import models as mod
from src.core.path import PATH
from src.db.database import execute_query
from src.db.utils.redis import CashManager

router = APIRouter()
logger = logging.getLogger()
queue = logging.getLogger("queue")


templates = Jinja2Templates(directory=os.path.join(PATH, "server", "templates"))
docs = os.path.join(PATH, "docs")


configs = [
    {
        "name": "Config Name",
        "PrivateKey": "GLzrInt9vGguqXi8r+Dli6K5CCzSe/5Zg8OH8wfk4V8=",
        "Address": "10.1.0.181/32",
        "DNS": " 10.0.0.1,9.9.9.9",
        "PublicKey": "xlaQzDNN/L5VWGVfW2r4pR9ufa0tr0kXwA1U2kilNho=",
        "AllowedIPs": "0.0.0.0/0",
        "Endpoint": "185.242.107.63:51830",
        "PersistentKeepalive": "25",
    }
] * 5


@router.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    query = select(mod.News).order_by(mod.News.id)
    news: list[mod.News] = (await execute_query(query)).scalars().all()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "news": [
                {
                    "date": new.date.ctime().replace("00:00:00", ""),
                    "title": new.title,
                    "excerpt": new.excerpt,
                    "id": f"news{new.id}",
                }
                for new in news
            ],
            "news_content": {
                f"news{new.id}": {"title": new.content_title, "content": new.content}
                for new in news
            },
        },
    )


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    user: Annotated[User, Depends(User.from_request)],
):
    return templates.TemplateResponse(
        "profile.html", {"request": request, "configsData": configs}
    )


@router.get("/auth", response_class=HTMLResponse)
async def auth_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})


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


# @router.get("/pricing", response_class=HTMLResponse)
# async def pricing_page(request: Request):
#     return templates.TemplateResponse("pricing.html", {"request": request})


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


# @router.get("/docs/{path:path}", response_class=HTMLResponse)
# async def open_docs(request: Request, path: str):
#     """Возвращает HTML-страницу по указанному пути.

#     Args:
#         request (Request): Объект запроса.
#         path (str): Путь к HTML-файлу.

#     Returns:
#         HTMLResponse: Рендеренная HTML-страница.
#     """
#     return docs.TemplateResponse(path, {"request": request})


@router.get("/docs/{path:path}", response_class=FileResponse)
async def open_docs(request: Request, path: str):
    """Возвращает статическую HTML-страницу по указанному пути.

    Args:
        request (Request): Объект запроса.
        path (str): Путь к HTML-файлу.

    Returns:
        FileResponse: Статическая HTML-страница.
    """
    file_path = os.path.join(docs, path)

    # Проверяем, существует ли файл
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    else:
        return FileResponse(os.path.join(docs, "404.html"))


@router.get("/{path:path}", response_class=HTMLResponse)
async def not_found(request: Request):
    return templates.TemplateResponse("404.html", {"request": request})
