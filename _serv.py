#!./.venv/bin/python


import logging
import logging.config
import os
import sys
from datetime import datetime

import sentry_sdk
import uvicorn
from fastapi import FastAPI, Form, HTTPException, Response, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastui import prebuilt_html
from fastui.auth import fastapi_auth_exception_handling
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

sys.path.insert(1, os.path.join(sys.path[0], "server"))
sys.path.insert(1, os.path.join(sys.path[0], "src"))

from server.err import RequiresLoginException
from server.fast_pages.auth import router as admin_auth_router
# from server.pages.auth import router as auth_router
from server.fast_pages.form import router as form_router
from server.fast_pages.main import router as main_router
from server.fast_pages.reports import router as reports_router
from server.fast_pages.tables import router as tables_router
from server.pages.index import router as index_router
from src.app import models as mod
from src.core.path import PATH
from src.db.utils import confirm_success_pay

server_log = "./server/log.ini"
logging.config.fileConfig(server_log, disable_existing_loggers=False)
logger = logging.getLogger()
queue = logging.getLogger("queue")

sentry_sdk.init(
    dsn="https://eda1429f1d444778a00f99681c553f7b@app.glitchtip.com/9075",
    integrations=[
        AsyncioIntegration(),
        LoggingIntegration(
            level=logging.ERROR,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR,  # Send records as events
        ),
    ],
)


app = FastAPI()
static = StaticFiles(directory=os.path.join(PATH, "server", "static"))
bugs = StaticFiles(directory=os.path.join(PATH, "bugs"))
favicon_path = os.path.join(PATH, "server", "static", "favicon.ico")


@app.exception_handler(RequiresLoginException)
async def exception_handler(*args, **kwargs) -> Response:
    return RedirectResponse(url="/vpn/auth", status_code=status.HTTP_302_FOUND)


fastapi_auth_exception_handling(app)
app.include_router(form_router, prefix="/api/bot/bug")
app.include_router(admin_auth_router, prefix="/api/bot/auth")
# app.include_router(auth_router, prefix="/vpn/auth")
app.include_router(tables_router, prefix="/api/bot/tables")
app.include_router(reports_router, prefix="/api/bot/tables/reports")
app.include_router(main_router, prefix="/api/bot")
app.include_router(index_router, prefix="/vpn")
app.mount("/static", static, name="static")
app.mount("/bugs", bugs, name="bugs")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/test")
def test_message(name: str | None = None):
    return {"message": f"Hello {name}"}


@app.post("/bot/notice")
async def receive_pay_data(
    notification_type: str = Form(default=""),
    operation_id: str = Form(default=0),
    amount: float = Form(default=0.0),
    withdraw_amount: float = Form(default=0.0),
    currency: str = Form(default=""),
    datetime: datetime = Form(default=datetime(1999, 1, 30, 0, 0, 0, 0)),
    sender: str = Form(default=""),
    codepro: bool = Form(default=False),
    label: str = Form(default="00000000-0000-0000-0000-000000000000"),
    sha1_hash: str = Form(default=""),
    test_notification: bool = Form(default=None),
    unaccepted: bool = Form(default=None),
):
    data = {
        "notification_type": notification_type,
        "transaction_id": operation_id,
        "amount": amount,
        "withdraw_amount": withdraw_amount,
        "currency": currency,
        "date": datetime,
        "sender": sender,
        "codepro": codepro,
        "label": label,
        "sha1_hash": sha1_hash,
        "test_notification": test_notification,
        "unaccepted": unaccepted,
    }
    try:
        logger.info("Принято уведомление об оплате", extra=data)

        transaction: mod.Transactions = await confirm_success_pay(
            mod.Transactions(**data)
        )
        if transaction:
            logger.info(f"Обновлены данные по транзакции {transaction}")
            queue.info(
                "Регистрация транзакции в очереди",
                extra={
                    "type": "TRANSACTION",
                    "user_id": transaction.user_id,
                    "label": label,
                    "amount": transaction.amount,
                },
            )
        else:
            logger.warning(f"Транзакция {label} не найдена в базе")
    except Exception as e:
        logger.exception("Ошибка обработки уведомления")
        raise HTTPException(status_code=500, detail=e)
    else:
        return {"status": str(transaction)}


@app.get("/bot/{path:path}")
async def html_landing() -> HTMLResponse:
    return HTMLResponse(prebuilt_html(title="Dan VPN"))


if __name__ == "__main__":
    # with open("./logs/server.log", "w"), open("./logs/psql_serv.log", "w"):
    #     ...
    uvicorn.run(
        "_serv:app",
        # host="127.0.0.1",
        host="172.17.0.1",
        port=5000,
        # workers=4,
        # reload=True,
        log_config=server_log,
        log_level="info",
        use_colors=False,
    )
