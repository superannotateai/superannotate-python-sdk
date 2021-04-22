class AppException(Exception):
    """
    Base exception for Licensee App. All exceptions thrown by inviter should
    extend this.
    """

    def __init__(self, message):
        super().__init__(message)

        self.message = message


class AppValidationException(AppException):
    """
    App validation exception
    """
