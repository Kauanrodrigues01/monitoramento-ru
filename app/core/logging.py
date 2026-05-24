import logging
import logging.config
import sys

from core.settings import settings

_ANSI_RESET = "\033[0m"
_LEVEL_COLORS = {
    "DEBUG": "\033[36m",  # cyan
    "INFO": "\033[32m",  # green
    "WARNING": "\033[33m",  # yellow
    "ERROR": "\033[31m",  # red
    "CRITICAL": "\033[1;31m",  # bold red
}

_FMT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


class _ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelname, _ANSI_RESET)
        record.levelname = f"{color}{record.levelname}{_ANSI_RESET}"
        return super().format(record)


def setup_logging() -> None:
    log_level = settings.LOG_LEVEL.upper()

    formatter_class = (
        "core.logging._ColorFormatter"
        if settings.LOG_ENV == "development"
        else "logging.Formatter"
    )

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": formatter_class,
                "fmt": _FMT,
                "datefmt": _DATE_FMT,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default",
            },
        },
        "loggers": {
            # silencia logs verbosos de libs externas
            "sqlalchemy.engine": {"level": "WARNING"},
            "uvicorn.access": {"level": "WARNING"},
            "asyncio": {"level": "WARNING"},
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
    }

    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
