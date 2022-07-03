import logging.config
import os
from logging import Formatter
from logging.handlers import RotatingFileHandler
from os.path import expanduser

import superannotate.lib.core as constances

default_logger = None

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "consoleFormatter",
                "stream": "ext://sys.stdout",
            },
        },
        "formatters": {
            "consoleFormatter": {
                "format": "SA-PYTHON-SDK - %(levelname)s - %(message)s",
            },
        },
        "loggers": {"sa": {"handlers": ["console"], "level": "DEBUG"}},
    }
)


def get_default_logger():
    global default_logger
    if not default_logger:
        default_logger = logging.getLogger("sa")
        try:
            log_file_path = expanduser(constances.LOG_FILE_LOCATION)
            open(log_file_path, "w").close()
            if os.access(log_file_path, os.W_OK):
                file_handler = RotatingFileHandler(
                    expanduser(constances.LOG_FILE_LOCATION),
                    maxBytes=5 * 1024 * 1024,
                    backupCount=5,
                    mode="a",
                )
                formatter = Formatter(
                    "SA-PYTHON-SDK - %(levelname)s - %(asctime)s - %(message)s"
                )
                file_handler.setFormatter(formatter)
                file_handler.setLevel("DEBUG")
                default_logger.addHandler(file_handler)
        except OSError:
            pass
    return default_logger
