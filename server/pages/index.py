import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from server.pages.auth import User
from src.app import models as mod
from src.core.path import PATH
from src.db.database import execute_query

router = APIRouter()
logger = logging.getLogger()
queue = logging.getLogger("queue")


templates = Jinja2Templates(directory=os.path.join(PATH, "server", "templates"))


@router.get("/", response_class=HTMLResponse)
async def main_page(
    request: Request,
    user: Annotated[User, Depends(User.from_request_opt)],
):
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
            "name": "Профиль" if user else "Войти",
        },
    )


@router.get("/about", response_class=HTMLResponse)
async def about_page(
    request: Request,
    user: Annotated[User, Depends(User.from_request_opt)],
):
    return templates.TemplateResponse("about.html", {"request": request})


@router.get("/500", response_class=HTMLResponse)
async def internal_error(request: Request):
    return templates.TemplateResponse("500.html", {"request": request})


@router.get("/{path:path}", response_class=HTMLResponse)
async def not_found(request: Request):
    return templates.TemplateResponse("404.html", {"request": request})
