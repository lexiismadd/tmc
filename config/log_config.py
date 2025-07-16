from config.settings import settings
import logging
from logging.config import dictConfig
import colorlog

# Configure logging
log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "coloured": {
            "()": "colorlog.ColoredFormatter",
            "format": "%(log_color)s%(levelprefix)s %(asctime)s - %(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "log_colors": {
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            }
        },
    },
    "handlers": {
        "default": {
            "formatter": "coloured",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "": {"handlers": ["default"], "level": settings.log_level.upper()},
        "uvicorn.access": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False
        },
        "uvicorn.error": {
            "level": "WARNING",
            "propagate": False
        },
        "httpx": {
            "level": "WARNING",
            "propagate": False
        },
    },
}
