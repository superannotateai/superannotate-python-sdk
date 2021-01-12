import logging

from . import common

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


class SAImageSizeTooLarge(SABaseException):
    def __init__(self, file_size, file_name=""):
        super().__init__(
            0, "Image " + file_name + " size " + str(file_size // 1024**2) +
            " MB is larger than " + str(common.MAX_IMAGE_SIZE // 1024**2) +
            " MB limit."
        )


class SAExistingProjectNameException(SABaseException):
    pass


class SANonExistingProjectNameException(SABaseException):
    pass


class SAExistingAnnotationClassNameException(SABaseException):
    pass


class SANonExistingAnnotationClassNameException(SABaseException):
    pass


class SAExistingExportNameException(SABaseException):
    pass


class SANonExistingExportNameException(SABaseException):
    pass
