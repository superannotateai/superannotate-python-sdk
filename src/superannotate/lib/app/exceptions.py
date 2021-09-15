from lib.core.exceptions import AppException


class PathError(AppException):
    """
    User input Error
    """


class EmptyOutputError(AppException):
    """
    Empty Output Error
    """
