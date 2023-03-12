import logging.config
import os
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
