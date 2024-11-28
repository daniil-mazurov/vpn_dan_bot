import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from src.core.path import PATH

router = APIRouter()
logger = logging.getLogger()


templates = Jinja2Templates(directory=os.path.join(PATH, "server", "templates"))
docs = os.path.join(PATH, "docs")


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


@router.get("/code/{path:path}", response_class=FileResponse)
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
