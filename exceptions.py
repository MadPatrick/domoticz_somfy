"""Tahoma exceptions."""


class TahomaException(Exception):
    """Base class for exceptions."""
    def __init__(self, message="Error message not defined"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return str(self.message)
        
class TooManyRetries(TahomaException):
    """Too many retries to call API"""
    def __init__(self):
        self.message = "Failed to call Tahoma/Somfy API (too many retries)"
        super().__init__(self.message)

class FailureWithErrorCode(TahomaException):
    """Too many retries to call API"""
    def __init__(self, code):
        self.message = "Failed to call Tahoma/Somfy API (return code = {})".format(code)
        super().__init__(self.message)

class FailureWithoutErrorCode(TahomaException):
    """Too many retries to call API"""
    def __init__(self):
        self.message = "Failed to call Tahoma/Somfy API (no return code )"
        super().__init__(self.message)

class LoginFailure(TahomaException):
    """failed to login to API"""
    def __init__(self, login_message = "Failed to login"):
        self.message = login_message
        super().__init__(self.message)

class NoListenerFailure(TahomaException):
    def __init__(self):
        self.message = "Trying to fetch events without listener registered"
        super().__init__(self.message)
    