import logging.config
from os.path import expanduser

import superannotate.lib.core as constances

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
            "fileHandler": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "fileFormatter",
                "filename": expanduser(constances.LOG_FILE_LOCATION),
                "mode": "a",
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 5,
            },
        },
        "formatters": {
            "consoleFormatter": {
                "format": "SA-PYTHON-SDK - %(levelname)s - %(message)s",
            },
            "fileFormatter": {
                "format": "SA-PYTHON-SDK - %(levelname)s - %(asctime)s - %(message)s"
            },
        },
        "loggers": {"sa": {"handlers": ["console", "fileHandler"], "level": "DEBUG"}},
    }
)


def get_default_logger():
    logger = logging.getLogger("sa")
    return logger
