import logging

logger = logging.getLogger("superannotate-python-sdk")


class SABaseException(Exception):
    def __init__(
        self,
        status_code='Unknown Status Code',
        message='Unknown Error Message'
    ):
        self.status_code = status_code
        self.message = message
        super().__init__(status_code, message)
