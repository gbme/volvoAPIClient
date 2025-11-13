"""
OAuth2 Authentication for Volvo Cars API

This module handles OAuth2 authentication flow including:
- Authorization URL generation
- Token exchange
- Token refresh
- PKCE (Proof Key for Code Exchange) support
"""

import base64
import hashlib
import json
import logging
import os
import secrets
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from .exceptions import AuthenticationError, InvalidTokenError


class VolvoAuth:
    """
    Handles OAuth2 authentication for Volvo Cars API
    """

    # Volvo OAuth2 endpoints
    AUTH_BASE_URL = "https://volvoid.eu.volvocars.com"
    AUTH_ENDPOINT = f"{AUTH_BASE_URL}/as/authorization.oauth2"
    TOKEN_ENDPOINT = f"{AUTH_BASE_URL}/as/token.oauth2"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: Optional[List[str]] = None,
        use_pkce: bool = True,
        token_storage_path: Optional[str] = None,
    ):
        """
        Initialize Volvo authentication

        Args:
            client_id: Your application's client ID
            client_secret: Your application's client secret
            redirect_uri: Registered redirect URI for your application
            scopes: List of requested scopes (permissions)
            use_pkce: Whether to use PKCE (recommended for security)
            token_storage_path: Path to store tokens persistently
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes or [
            "openid",
            "conve:battery_charge_level",
            "conve:commands",
            "conve:brake_status",
            "conve:diagnostics_engine_status",
            "conve:fuel_status",
            "conve:vehicle_relation",
            "conve:warnings",
        ]
        self.use_pkce = use_pkce
        self.token_storage_path = token_storage_path or "tokens.json"

        # Setup logger for debugging
        self.logger = logging.getLogger(__name__)

        # Token storage
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

        # PKCE parameters
        self._code_verifier: Optional[str] = None
        self._code_challenge: Optional[str] = None

        # Load existing tokens if available
        self._load_tokens()

    def _generate_pkce_parameters(self) -> Tuple[str, str]:
        """
        Generate PKCE code verifier and challenge

        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate code verifier (43-128 character string)
        self._code_verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )

        # Generate code challenge (SHA256 hash of verifier)
        challenge_bytes = hashlib.sha256(self._code_verifier.encode("utf-8")).digest()
        self._code_challenge = (
            base64.urlsafe_b64encode(challenge_bytes).decode("utf-8").rstrip("=")
        )

        return self._code_verifier, self._code_challenge

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate authorization URL for OAuth2 flow

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
        }

        if state:
            params["state"] = state

        if self.use_pkce:
            self._generate_pkce_parameters()
            params["code_challenge"] = self._code_challenge
            params["code_challenge_method"] = "S256"

        return f"{self.AUTH_ENDPOINT}?{urlencode(params)}"

    def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, any]:
        """
        Exchange authorization code for access and refresh tokens

        Args:
            authorization_code: Code received from authorization callback

        Returns:
            Dictionary containing token information

        Raises:
            AuthenticationError: If token exchange fails
        """
        # Prepare authentication header
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}",
        }

        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self.redirect_uri,
        }

        # Add PKCE verifier if used
        if self.use_pkce and self._code_verifier:
            data["code_verifier"] = self._code_verifier

        try:
            response = requests.post(self.TOKEN_ENDPOINT, headers=headers, data=data)
            response.raise_for_status()

            token_data = response.json()

            # Store tokens
            self._access_token = token_data.get("access_token")
            self._refresh_token = token_data.get("refresh_token")

            # Calculate expiration time
            expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)

            # Save tokens to file
            self._save_tokens()

            return token_data

        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Token exchange failed: {str(e)}")

    def refresh_access_token(self) -> Dict[str, any]:
        """
        Refresh the access token using refresh token

        Returns:
            Dictionary containing new token information

        Raises:
            AuthenticationError: If token refresh fails
        """
        if not self._refresh_token:
            self.logger.debug("Token refresh attempted but no refresh token available")
            raise AuthenticationError("No refresh token available")

        # Log refresh attempt
        current_expiry = (
            self._token_expires_at.isoformat() if self._token_expires_at else "unknown"
        )
        self.logger.info(
            "🔄 Refreshing access token (current expires: %s)", current_expiry
        )

        # Prepare authentication header
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}",
        }

        data = {"grant_type": "refresh_token", "refresh_token": self._refresh_token}

        try:
            self.logger.debug("Making token refresh request to %s", self.TOKEN_ENDPOINT)
            response = requests.post(
                self.TOKEN_ENDPOINT, headers=headers, data=data, timeout=30
            )
            response.raise_for_status()

            token_data = response.json()
            self.logger.debug("Token refresh response received successfully")

            # Update tokens
            old_access_token = (
                self._access_token[:20] + "..." if self._access_token else None
            )
            self._access_token = token_data.get("access_token")

            # Some implementations return new refresh token, some don't
            new_refresh_token = token_data.get("refresh_token")
            if new_refresh_token:
                self.logger.debug("New refresh token received in response")
                self._refresh_token = new_refresh_token
            else:
                self.logger.debug(
                    "Using existing refresh token (none provided in response)"
                )

            # Calculate expiration time
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)

            new_access_token = (
                self._access_token[:20] + "..." if self._access_token else None
            )
            new_expiry = self._token_expires_at.isoformat()

            self.logger.info(
                "✅ Token refresh successful! New token expires: %s", new_expiry
            )
            self.logger.debug(
                "Token changed from %s to %s", old_access_token, new_access_token
            )

            # Save updated tokens
            self._save_tokens()
            self.logger.debug("Updated tokens saved to %s", self.token_storage_path)

            return token_data

        except requests.exceptions.RequestException as e:
            self.logger.error("❌ Token refresh failed: %s", str(e))
            raise AuthenticationError(f"Token refresh failed: {str(e)}") from e

    def get_access_token(self) -> str:
        """
        Get valid access token, refreshing if necessary

        Returns:
            Valid access token

        Raises:
            InvalidTokenError: If no valid token is available
        """
        if not self._access_token:
            self.logger.debug("No access token available")
            raise InvalidTokenError(
                "No access token available. Please authenticate first."
            )

        # Check if token is expired (with 5 minute buffer)
        now = datetime.now()
        if self._token_expires_at:
            time_until_expiry = self._token_expires_at - now
            buffer_time = self._token_expires_at - timedelta(minutes=5)

            self.logger.debug(
                "Checking token expiry: expires at %s, buffer at %s, now is %s",
                self._token_expires_at.isoformat(),
                buffer_time.isoformat(),
                now.isoformat(),
            )

            if now >= buffer_time:
                self.logger.info(
                    "🕐 Token expires soon (in %s), refreshing...",
                    str(time_until_expiry),
                )

                if self._refresh_token:
                    try:
                        self.refresh_access_token()
                    except AuthenticationError as exc:
                        self.logger.error(
                            "Token refresh failed, re-authentication required"
                        )
                        raise InvalidTokenError(
                            "Token expired and refresh failed. Please re-authenticate."
                        ) from exc
                else:
                    self.logger.error("Token expired but no refresh token available")
                    raise InvalidTokenError(
                        "Token expired and no refresh token available. Please re-authenticate."
                    )
            else:
                self.logger.debug(
                    "Token is valid, expires in %s", str(time_until_expiry)
                )
        else:
            self.logger.warning(
                "No token expiration time available, using current token"
            )

        return self._access_token

    def is_authenticated(self) -> bool:
        """
        Check if user is currently authenticated

        Returns:
            True if authenticated with valid token
        """
        try:
            self.get_access_token()
            self.logger.debug("Authentication check: valid token available")
            return True
        except InvalidTokenError as e:
            self.logger.debug("Authentication check failed: %s", str(e))
            return False

    def logout(self):
        """
        Clear all stored tokens and authentication state
        """
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = None
        self._code_verifier = None
        self._code_challenge = None

        # Remove stored tokens file
        if os.path.exists(self.token_storage_path):
            os.remove(self.token_storage_path)

    def _save_tokens(self):
        """Save tokens to persistent storage"""
        if not self.token_storage_path:
            self.logger.debug("No token storage path configured, skipping save")
            return

        token_data = {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "expires_at": (
                self._token_expires_at.isoformat() if self._token_expires_at else None
            ),
        }

        try:
            with open(self.token_storage_path, "w", encoding="utf-8") as f:
                json.dump(token_data, f, indent=2)
            self.logger.debug("💾 Tokens saved to %s", self.token_storage_path)
        except IOError as e:
            self.logger.warning(
                "Failed to save tokens to %s: %s", self.token_storage_path, str(e)
            )

    def _load_tokens(self):
        """Load tokens from persistent storage"""
        if not self.token_storage_path:
            self.logger.debug("No token storage path configured, skipping load")
            return

        if not os.path.exists(self.token_storage_path):
            self.logger.debug(
                "Token file %s does not exist, starting fresh", self.token_storage_path
            )
            return

        try:
            with open(self.token_storage_path, "r", encoding="utf-8") as f:
                token_data = json.load(f)

            self._access_token = token_data.get("access_token")
            self._refresh_token = token_data.get("refresh_token")

            expires_at_str = token_data.get("expires_at")
            if expires_at_str:
                self._token_expires_at = datetime.fromisoformat(expires_at_str)
                self.logger.debug(
                    "📂 Loaded tokens from %s (expires: %s)",
                    self.token_storage_path,
                    expires_at_str,
                )
            else:
                self.logger.debug(
                    "📂 Loaded tokens from %s (no expiry info)", self.token_storage_path
                )

        except (IOError, json.JSONDecodeError, ValueError) as e:
            self.logger.warning(
                "Failed to load tokens from %s: %s", self.token_storage_path, str(e)
            )

    @staticmethod
    def extract_code_from_callback_url(callback_url: str) -> Tuple[str, Optional[str]]:
        """
        Extract authorization code and state from callback URL

        Args:
            callback_url: The full callback URL received after authorization

        Returns:
            Tuple of (authorization_code, state)

        Raises:
            AuthenticationError: If no code found in URL
        """
        parsed = urlparse(callback_url)
        params = parse_qs(parsed.query)

        # Check for error first
        if "error" in params:
            error_code = params["error"][0]
            error_description = params.get("error_description", ["Unknown error"])[0]
            raise AuthenticationError(
                f"Authorization failed: {error_code} - {error_description}"
            )

        # Extract code
        code_list = params.get("code")
        if not code_list:
            raise AuthenticationError("No authorization code found in callback URL")

        code = code_list[0]
        state = params.get("state", [None])[0]

        return code, state
