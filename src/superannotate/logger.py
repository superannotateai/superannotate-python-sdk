import logging.config
import os
from logging import Formatter
from logging.handlers import RotatingFileHandler

import superannotate.lib.core as constances


loggers = {}


def get_server_logger():
    global loggers
    if loggers.get("sa_server"):
        return loggers.get("sa_server")
    else:
        logger = logging.getLogger("sa_server")
        logger.propagate = False
        logger.setLevel(logging.INFO)
        stream_handler = logging.StreamHandler()
        logger.addHandler(stream_handler)
        try:
            log_file_path = os.path.join(constances.LOG_FILE_LOCATION, "sa_server.log")
            if os.access(log_file_path, os.W_OK):
                file_handler = RotatingFileHandler(
                    log_file_path,
                    maxBytes=5 * 1024 * 1024,
                    backupCount=2,
                    mode="a",
                )
                logger.addHandler(file_handler)
        except OSError:
            pass
        finally:
            loggers["sa_server"] = logger
            return logger


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
            log_file_path = os.path.join(constances.LOG_FILE_LOCATION, "sa.log")
            open(log_file_path, "w").close()
            if os.access(log_file_path, os.W_OK):
                file_handler = RotatingFileHandler(
                    log_file_path,
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
