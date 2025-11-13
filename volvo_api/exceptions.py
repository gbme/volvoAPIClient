"""
Custom exceptions for Volvo API client
"""


class VolvoAPIError(Exception):
    """Base exception for Volvo API errors"""

    def __init__(
        self, message: str, status_code: int = None, response_data: dict = None
    ):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)


class AuthenticationError(VolvoAPIError):
    """Raised when authentication fails"""

    pass


class AuthorizationError(VolvoAPIError):
    """Raised when authorization fails"""

    pass


class RateLimitError(VolvoAPIError):
    """Raised when rate limit is exceeded"""

    pass


class InvalidTokenError(AuthenticationError):
    """Raised when token is invalid or expired"""

    pass


class VehicleNotFoundError(VolvoAPIError):
    """Raised when vehicle is not found or not accessible"""

    pass


class ValidationError(VolvoAPIError):
    """Raised when request data validation fails"""

    pass
