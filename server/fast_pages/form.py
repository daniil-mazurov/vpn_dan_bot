import logging
import os
from datetime import date
from typing import Annotated
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, Depends, UploadFile
from fastui import FastUI
from fastui import components as c
from fastui.events import GoToEvent, PageEvent
from fastui.forms import FormFile, Textarea  # , fastui_form
from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from core.config import settings
from core.exceptions import UniquenessError
from core.path import PATH
from db.models import Reports
from db.utils import add_report
from server.fast_pages.shared import bot_page, patched_fastui_form
from server.utils.auth_user import User

router = APIRouter()
logger = logging.getLogger()
queue = logging.getLogger("queue")

UPLOAD_DIRECTORY = os.path.join(PATH, "bugs")  # Папка для загрузки файлов
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)


class BugModel(BaseModel):
    user_name: str | None = Field(
        None,
        title="Name",
        description="Представьтесь, чтобы мы знали как к вам обращаться",
    )

    telegram_id: int = Field(
        title="ID",
        description="Ваш ID в Telegram",
    )

    bug_info: Annotated[str, Textarea(rows=5)] = Field(
        title="Info", description="Описание вашей проблемы", max_length=1000
    )

    pics: (
        Annotated[list[UploadFile], FormFile(accept="image/*", max_size=3_100_000)]
        | None
    ) = Field(
        None,
        title="Pictures",
        description="Скриншоты проблемы. "
        "Если у вас проблемы с оплатой обязательно приложите скриншот совершенной транзакции (чек).",
        max_length=5,
    )

    date_of: date = Field(
        title="Date",
        description="Когда вы наблюдали проблему?",
    )

    human: bool = Field(
        title="Is human",
        description="Are you human?",
        json_schema_extra={"mode": "switch"},
    )

    @field_validator("human")
    def human_validator(cls, v: bool) -> bool:
        if v is False:
            raise PydanticCustomError(
                "Human", "Необходимо подтверждение того, что вы человек"
            )
        return v


@router.get("/error", response_model=FastUI, response_model_exclude_none=True)
async def redirect_bug():
    return bot_page(c.FireEvent(event=GoToEvent(url="/bot/bug/create")))


@router.get("/create", response_model=FastUI, response_model_exclude_none=True)
async def form_content(
    user: Annotated[User | None, Depends(User.from_request_opt)],
    name: str | None = None,
    telegram_id: int | None = None,
):
    return bot_page(
        c.Heading(text="Опишите вашу проблему", level=2),
        c.ModelForm(
            model=BugModel,
            display_mode="page",
            submit_url="/api/bot/bug/send",
            initial=dict(user_name=name, telegram_id=telegram_id, date_of=date.today()),
            loading=[c.Spinner(text="Хорошо, отправляю ваш отчет...")],
        ),
        user=user,
        title="Отправить отчет о проблеме",
    )


@router.post("/send", response_model=FastUI, response_model_exclude_none=True)
async def big_form_post(form: Annotated[BugModel, patched_fastui_form(BugModel)]):
    try:
        logger.info("Принято сообщение о проблеме", extra=dict(form))

        pic_map = {}
        folder = str(uuid4())
        for in_file in form.pics:
            content = await in_file.read()

            if content:
                os.makedirs(os.path.join(UPLOAD_DIRECTORY, folder), exist_ok=True)
                file_location = os.path.join(UPLOAD_DIRECTORY, folder, in_file.filename)

                async with aiofiles.open(file_location, "wb") as out_file:
                    await out_file.write(content)

                pic_map[in_file.filename] = folder

        report = Reports.ValidationSchema(
            user_id=form.telegram_id,
            user_name=form.user_name,
            info=form.bug_info,
            pictures=pic_map,
            create_date=form.date_of,
        ).model_dump(exclude={"id", "updated", "site_updated"})

        report = await add_report(report)

        queue.info(
            "Зарегистрировано обращение",
            extra={
                "type": "REPORT",
                "user_id": report.user_id,
                "label": report.id,
                "amount": None,
            },
        )

    except Exception as e:
        logger.exception("Ошибка регистрации формы обращения в техподдержку")

        err_msg = "Сожалеем, однако при отправке формы произошла ошибка. Пожалуйста попробуйте позже."

        if isinstance(e, UniquenessError):
            err_msg = "Ваш Telegram ID не найден в базе."

        return [
            c.FireEvent(event=PageEvent(name="send-error")),
            c.Modal(
                title="Ошибка!",
                body=[c.Paragraph(text=err_msg)],
                footer=[
                    c.Button(text="Принято", on_click=GoToEvent(url="/bot/bug/error"))
                ],
                open_trigger=PageEvent(name="send-error"),
            ),
        ]
    else:
        return [
            c.FireEvent(event=PageEvent(name="bug-sended")),
            c.Modal(
                title="Успешно!",
                body=[
                    c.Paragraph(
                        text="Ваш отчет об ошибке успешно отправлен и будет обработан в ближайшее время"
                    )
                ],
                footer=[
                    c.Button(
                        text="Принято",
                        on_click=GoToEvent(url=f"{settings.subserver_url}vpn"),
                    ),
                ],
                open_trigger=PageEvent(name="bug-sended"),
            ),
        ]
