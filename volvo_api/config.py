"""
Configuration management for Volvo API client
"""

import os
from typing import Dict, List, Optional

from dotenv import load_dotenv


class VolvoConfig:
    """Configuration management for Volvo API"""

    # Default scopes for various use cases
    DEFAULT_SCOPES = [
        "openid",
        "conve:battery_charge_level",
        "conve:commands",
        "conve:brake_status",
        "conve:diagnostics_engine_status",
        "conve:fuel_status",
        "conve:vehicle_relation",
        "conve:warnings",
        # Energy API v2 scopes
        "energy:state:read",
        "energy:capability:read",
        # Location API scope
        "location:read",
    ]

    BASIC_SCOPES = [
        "openid",
        "conve:vehicle_relation",
        "conve:fuel_status",
        "conve:battery_charge_level",
        # Basic energy access
        "energy:state:read",
    ]

    COMMAND_SCOPES = ["openid", "conve:commands", "conve:vehicle_relation"]

    ALL_AVAILABLE_SCOPES = [
        "openid",
        "conve:battery_charge_level",
        "conve:commands",
        "conve:brake_status",
        "conve:diagnostics_engine_status",
        "conve:fuel_status",
        "conve:vehicle_relation",
        "conve:warnings",
        "conve:climatization_start_stop",
        "conve:engine_start_stop",
        "conve:honk_blink",
        "conve:lock_unlock",
        "conve:preclimatization",
        "conve:trip_statistics",
        # Energy API v2 scopes
        "energy:state:read",
        "energy:capability:read",
        # Location API scopes
        "location:read",
    ]

    def __init__(self, env_file: str = ".env"):
        """
        Initialize configuration

        Args:
            env_file: Path to environment file
        """
        # Load environment variables
        if os.path.exists(env_file):
            load_dotenv(env_file)

    @property
    def client_id(self) -> Optional[str]:
        """Get client ID from environment"""
        return os.getenv("VOLVO_CLIENT_ID")

    @property
    def client_secret(self) -> Optional[str]:
        """Get client secret from environment"""
        return os.getenv("VOLVO_CLIENT_SECRET")

    @property
    def redirect_uri(self) -> Optional[str]:
        """Get redirect URI from environment"""
        return os.getenv("VOLVO_REDIRECT_URI")

    @property
    def vin(self) -> Optional[str]:
        """Get VIN from environment"""
        return os.getenv("VOLVO_VIN")

    @property
    def vcc_api_key(self) -> Optional[str]:
        """Get VCC API key from environment"""
        return os.getenv("VOLVO_VCC_API_KEY")

    @property
    def api_base_url(self) -> str:
        """Get API base URL from environment or default"""
        return os.getenv("VOLVO_API_BASE_URL", "https://api.volvocars.com")

    @property
    def auth_base_url(self) -> str:
        """Get auth base URL from environment or default"""
        return os.getenv("VOLVO_AUTH_BASE_URL", "https://volvoid.eu.volvocars.com")

    def validate(self) -> List[str]:
        """
        Validate configuration and return list of missing required fields

        Returns:
            List of missing required field names
        """
        missing = []

        if not self.client_id:
            missing.append("VOLVO_CLIENT_ID")
        if not self.client_secret:
            missing.append("VOLVO_CLIENT_SECRET")
        if not self.redirect_uri:
            missing.append("VOLVO_REDIRECT_URI")
        if not self.vcc_api_key:
            missing.append("VOLVO_VCC_API_KEY")

        return missing

    def is_valid(self) -> bool:
        """Check if configuration is valid"""
        return len(self.validate()) == 0

    def get_scopes_by_category(self, category: str = "default") -> List[str]:
        """
        Get scopes by category

        Args:
            category: Scope category ("default", "basic", "command", "all")

        Returns:
            List of scopes for the category
        """
        category_map = {
            "default": self.DEFAULT_SCOPES,
            "basic": self.BASIC_SCOPES,
            "command": self.COMMAND_SCOPES,
            "all": self.ALL_AVAILABLE_SCOPES,
        }

        return category_map.get(category.lower(), self.DEFAULT_SCOPES)

    def to_dict(self) -> Dict[str, Optional[str]]:
        """
        Convert configuration to dictionary

        Returns:
            Configuration as dictionary
        """
        return {
            "client_id": self.client_id,
            "client_secret": "***" if self.client_secret else None,  # Hide secret
            "redirect_uri": self.redirect_uri,
            "vin": self.vin,
            "api_base_url": self.api_base_url,
            "auth_base_url": self.auth_base_url,
        }
