#!./.venv/bin/python


import asyncio
import logging
import logging.config

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from src.parser import parse_args

logging.config.fileConfig("log.ini", disable_existing_loggers=False)
logger = logging.getLogger()


sentry_sdk.init(
    dsn="https://81a6f6b105d24e61a39e5aff703d0473@app.glitchtip.com/9074",
    integrations=[
        AsyncioIntegration(),
        LoggingIntegration(level=logging.ERROR, event_level=logging.ERROR),
    ],
    environment="development",
)


def main(args):
    """Точка входа"""

    logger.info(f"<{'=' * 10} BOT START {'=' * 10}>", extra=args.__dict__)
    asyncio.run(start_bot())
    logger.info("BOT CLOSE")


if __name__ == "__main__":
    logger.info("\n" * 5 + "#" * 20)

    for extra_logger in {logger.split(".")[0] for logger in logger.manager.loggerDict}:
        logging.getLogger(extra_logger).info(
            f"<{'=' * 10} {extra_logger.upper()} START {'=' * 10}>"
        )

    args = parse_args()

    from src.app import start_bot

    main(args)
