import logging.config
import os
from logging import Formatter
from logging.handlers import RotatingFileHandler
from os.path import expanduser

import superannotate.lib.core as constances


loggers = {}


def get_default_logger():
    global loggers
    if loggers.get("sa"):
        return loggers.get("sa")
    else:
        logger = logging.getLogger("sa")
        logger.propagate = False
        logger.setLevel(logging.INFO)
        stream_handler = logging.StreamHandler()
        formatter = Formatter("SA-PYTHON-SDK - %(levelname)s - %(message)s")
        stream_handler.setFormatter(formatter)
        # logger.handlers[0] = stream_handler
        logger.addHandler(stream_handler)
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
                file_formatter = Formatter(
                    "SA-PYTHON-SDK - %(levelname)s - %(asctime)s - %(message)s"
                )
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
        except OSError:
            pass
        finally:
            loggers["sa"] = logger
            return logger
