import json
import logging
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends
from fastui import AnyComponent, FastUI
from fastui import components as c
from fastui.auth import AuthRedirect
from fastui.events import AuthEvent, GoToEvent, PageEvent
from passlib.context import CryptContext
from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_core import PydanticCustomError

from core.config import settings
from db import models as mod
from server.fast_pages.shared import bot_page, patched_fastui_form
from server.utils.auth_user import User

router = APIRouter()
logger = logging.getLogger()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginForm(BaseModel):
    login: str = Field(
        title="Your login",
    )
    password: SecretStr = Field(
        title="Password",
        description="Enter your password",
        json_schema_extra={"autocomplete": "current-password"},
    )

    @field_validator("login")
    def login_validator(cls, login: str) -> str:
        if login != settings.ADMIN_LOGIN:
            raise PydanticCustomError("login", "Неверный login")
        return login

    @field_validator("password")
    def pass_validator(cls, password: SecretStr) -> str:
        if not pwd_context.verify(
            password.get_secret_value(), settings.ADMIN_HASH.get_secret_value()
        ):
            raise PydanticCustomError("password", "Неверный пароль")
        return password


@router.get("/login", response_model=FastUI, response_model_exclude_none=True)
async def auth_login(
    user: Annotated[User | None, Depends(User.from_request_opt)],
) -> list[AnyComponent]:
    if user is not None:
        # already logged in
        raise AuthRedirect("/bot/auth/profile")

    return bot_page(
        c.ModelForm(
            model=LoginForm, submit_url="/api/bot/auth/login", display_mode="page"
        ),
        user=user,
        title="Authentication",
    )


@router.post("/login", response_model=FastUI, response_model_exclude_none=True)
async def login_form_post(
    form: Annotated[LoginForm, patched_fastui_form(LoginForm)],
) -> list[AnyComponent]:
    user = User(login=form.login, extra={})
    token = user.encode_token()
    return [c.FireEvent(event=AuthEvent(token=token, url="/bot/auth/profile"))]


@router.get("/profile", response_model=FastUI, response_model_exclude_none=True)
async def profile(
    user: Annotated[User, Depends(User.from_request)],
) -> list[AnyComponent]:
    return bot_page(
        c.Div(
            components=[
                c.Paragraph(text=f'You are logged in as "{user.login}".'),
                c.Button(
                    text="Logout",
                    on_click=PageEvent(name="submit-form"),
                    class_name="+ ms-2",
                ),
            ],
            class_name="d-flex align-items-center",  # Используем Flexbox для горизонтального выравнивания
        ),
        c.Paragraph(text="\nAdmin instruments"),
        c.Div(
            components=[
                c.Link(
                    components=[c.Button(text="ErrorLog", named_style="secondary")],
                    on_click=GoToEvent(
                        url="https://app.glitchtip.com/danvpn/issues?query=is:unresolved"
                    ),
                    class_name="+ ms-2",
                ),
                c.Link(
                    components=[c.Button(text="PgAdmin4", named_style="secondary")],
                    on_click=GoToEvent(url=f"{settings.subserver_url}pgadmin"),
                    class_name="+ ms-2",
                ),
                c.Link(
                    components=[c.Button(text="Portainer", named_style="secondary")],
                    on_click=GoToEvent(url=f"{settings.subserver_url}portainer"),
                    class_name="+ ms-2",
                ),
                c.Link(
                    components=[c.Button(text="InfluxDB", named_style="secondary")],
                    on_click=GoToEvent(
                        url=f"http://{settings.subserver_url.host}:8086"
                    ),
                    class_name="+ ms-2",
                ),
                c.Link(
                    components=[c.Button(text="Grafana", named_style="secondary")],
                    on_click=GoToEvent(url=f"{settings.subserver_url}grafana"),
                    class_name="+ ms-2",
                ),
            ],
            class_name="d-flex align-items-center",  # Используем Flexbox для горизонтального выравнивания
        ),
        c.Form(
            submit_url="/api/bot/auth/logout",
            form_fields=[
                c.FormFieldInput(
                    name="test", title="", initial="data", html_type="hidden"
                )
            ],
            footer=[],
            submit_trigger=PageEvent(name="submit-form"),
        ),
        user=user,
        title=user.login.capitalize(),
    )


@router.post("/logout", response_model=FastUI, response_model_exclude_none=True)
async def logout_form_post() -> list[AnyComponent]:
    return [c.FireEvent(event=AuthEvent(token=False, url="/bot/auth/login"))]
