"""
Volvo Cars API Client Library

This library provides a Python interface for the Volvo Cars API,
implementing OAuth2 authentication and various API endpoints.
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from .auth import VolvoAuth
from .client import VolvoAPIClient
from .config import VolvoConfig
from .exceptions import AuthenticationError, RateLimitError, VolvoAPIError

__all__ = [
    "VolvoAuth",
    "VolvoAPIClient",
    "VolvoConfig",
    "VolvoAPIError",
    "AuthenticationError",
    "RateLimitError",
]
