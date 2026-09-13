class AppException(Exception):
    """
    Base exception for Licensee App. All exceptions thrown by inviter should
    extend this.
    """

    def __init__(self, message):
        super().__init__(message)

        self.message = str(message)

    def __str__(self):
        return self.message


class SAAuthError(AppException):
    """Credentials the SDK cannot act on.

    Raised when a token is missing, malformed, or does not grant what was asked for -
    the team or the organization. Distinguishing these from every other AppException
    lets a caller retry authentication rather than the operation, and lets telemetry
    recognise an auth failure by type instead of by matching on the message.

    Subclasses AppException, so existing ``except AppException`` still catches it.
    """


class BackendError(AppException):
    """
    Backend Error
    """


class AppValidationException(AppException):
    """
    App validation exception
    """


class ImageProcessingException(AppException):
    """
    App validation exception
    """


class PathError(AppException):
    """
    User input Error
    """


class FileChangedError(AppException):
    """
    User input Error
    """
