class AppException(Exception):
    """
    Base exception for Licensee App. All exceptions thrown by inviter should
    extend this.
    """

    def __init__(self, message):
        super().__init__(message)

        self.message = message

    def __str__(self):
        return self.message


class AppValidationException(AppException):
    """
    App validation exception
    """


class ImageProcessingException(AppException):
    """
    App validation exception
    """
