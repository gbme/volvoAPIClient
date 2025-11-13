"""
Volvo Cars API Client

This module provides a high-level interface to the Volvo Cars API,
handling authentication and providing methods for various API endpoints.
"""

import json
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from .auth import VolvoAuth
from .exceptions import (
    AuthenticationError,
    RateLimitError,
    ValidationError,
    VehicleNotFoundError,
    VolvoAPIError,
)


class VolvoAPIClient:
    """
    Main client for interacting with Volvo Cars API
    """

    # Volvo API base URL
    API_BASE_URL = "https://api.volvocars.com"

    def __init__(
        self,
        auth: VolvoAuth,
        vcc_api_key: str,
        api_base_url: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize Volvo API client

        Args:
            auth: Authenticated VolvoAuth instance
            vcc_api_key: VCC API key from your Volvo Developer Portal application
            api_base_url: Override default API base URL
            timeout: Request timeout in seconds
        """
        self.auth = auth
        self.vcc_api_key = vcc_api_key
        self.api_base_url = api_base_url or self.API_BASE_URL
        self.timeout = timeout

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Volvo API

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Form data
            json_data: JSON data

        Returns:
            JSON response data

        Raises:
            VolvoAPIError: For API errors
            AuthenticationError: For auth errors
            RateLimitError: When rate limited
        """
        # Get valid access token
        try:
            access_token = self.auth.get_access_token()
        except Exception as e:
            raise AuthenticationError(f"Failed to get access token: {str(e)}") from e

        # Build full URL
        url = urljoin(self.api_base_url, endpoint.lstrip("/"))

        # Prepare headers
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "vcc-api-key": self.vcc_api_key,
        }

        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                data=data,
                timeout=self.timeout,
            )

            # Handle different response codes
            if response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed - invalid or expired token"
                )
            elif response.status_code == 403:
                raise AuthenticationError("Access forbidden - insufficient permissions")
            elif response.status_code == 404:
                raise VehicleNotFoundError("Vehicle not found or not accessible")
            elif response.status_code == 429:
                raise RateLimitError("Rate limit exceeded", status_code=429)
            elif response.status_code >= 400:
                try:
                    error_data = response.json()
                except json.JSONDecodeError:
                    error_data = {"message": response.text}

                raise VolvoAPIError(
                    f"API request failed: {error_data.get('message', 'Unknown error')}",
                    status_code=response.status_code,
                    response_data=error_data,
                )

            response.raise_for_status()

            # Try to parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError:
                # Some endpoints might return empty responses
                return {"status": "success"}

        except requests.exceptions.RequestException as e:
            raise VolvoAPIError(f"Request failed: {str(e)}") from e

    def get_vehicles(self) -> List[Dict[str, Any]]:
        """
        Get list of vehicles associated with the account

        Returns:
            List of vehicle information
        """
        response = self._make_request("GET", "/connected-vehicle/v2/vehicles")
        return response.get("data", [])

    def get_vehicle_details(self, vin: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific vehicle

        Args:
            vin: Vehicle identification number

        Returns:
            Vehicle details
        """
        response = self._make_request("GET", f"/connected-vehicle/v2/vehicles/{vin}")
        return response.get("data", {})

    def get_energy_state(self, vin: str) -> Dict[str, Any]:
        """
        Get comprehensive energy state for electric/hybrid vehicle (Energy API v2)

        This includes battery charge level, electric range, charging status,
        charger connection status, and more energy-related information.

        Args:
            vin: Vehicle identification number

        Returns:
            Energy state information including:
            - batteryChargeLevel: Current battery charge (percentage)
            - electricRange: Estimated electric range
            - chargingStatus: Current charging status
            - chargerConnectionStatus: Charger connection status
            - chargingType: AC/DC charging type
            - targetBatteryChargeLevel: Target charge level
            - chargingPower: Current charging power
            - estimatedChargingTimeToTargetBatteryChargeLevel: Time to target
        """
        response = self._make_request("GET", f"/energy/v2/vehicles/{vin}/state")
        # Energy API v2 returns data directly, not wrapped in "data" field
        return response

    def get_energy_capabilities(self, vin: str) -> Dict[str, Any]:
        """
        Get energy capabilities for the vehicle (Energy API v2)

        Returns which energy-related endpoints and data points are supported
        for this specific vehicle.

        Args:
            vin: Vehicle identification number

        Returns:
            Energy capabilities information including supported features
        """
        response = self._make_request("GET", f"/energy/v2/vehicles/{vin}/capabilities")
        print(response)
        return response.get("data", {})

    def get_battery_charge_level(self, vin: str) -> Dict[str, Any]:
        """
        Get battery charge level for electric/hybrid vehicle

        This is a convenience method that extracts just the battery charge level
        from the full energy state. For comprehensive energy data, use get_energy_state().

        Args:
            vin: Vehicle identification number

        Returns:
            Battery charge level information
        """
        energy_state = self.get_energy_state(vin)
        battery_info = energy_state.get("batteryChargeLevel", {})

        # Return in a format consistent with other endpoints
        if battery_info.get("status") == "OK":
            return {"batteryChargeLevel": battery_info}
        else:
            return battery_info

    def get_fuel_status(self, vin: str) -> Dict[str, Any]:
        """
        Get fuel status for the vehicle

        Args:
            vin: Vehicle identification number

        Returns:
            Fuel status information
        """
        response = self._make_request(
            "GET", f"/connected-vehicle/v2/vehicles/{vin}/fuel"
        )
        return response.get("data", {})

    def get_odometer(self, vin: str) -> Dict[str, Any]:
        """
        Get odometer reading

        Args:
            vin: Vehicle identification number

        Returns:
            Odometer information
        """
        response = self._make_request(
            "GET", f"/connected-vehicle/v2/vehicles/{vin}/odometer"
        )
        return response.get("data", {})

    def get_location(self, vin: str) -> Dict[str, Any]:
        """
        Get vehicle location (if available and permitted)

        Args:
            vin: Vehicle identification number

        Returns:
            Location information
        """
        response = self._make_request("GET", f"/location/v1/vehicles/{vin}/location")
        return response.get("data", {})

    def get_engine_status(self, vin: str) -> Dict[str, Any]:
        """
        Get engine status and diagnostics (alias for get_energy_state)

        Note: This method is kept for compatibility but calls the same
        endpoint as get_energy_state since engine status is part of
        the energy state in Volvo's API.

        Args:
            vin: Vehicle identification number

        Returns:
            Energy state information (same as get_energy_state)
        """
        return self.get_energy_state(vin)

    def get_warnings(self, vin: str) -> List[Dict[str, Any]]:
        """
        Get vehicle warnings and alerts

        Args:
            vin: Vehicle identification number

        Returns:
            List of warnings
        """
        response = self._make_request(
            "GET", f"/connected-vehicle/v2/vehicles/{vin}/warnings"
        )
        return response.get("data", [])

    def get_doors_status(self, vin: str) -> Dict[str, Any]:
        """
        Get doors and windows status

        Args:
            vin: Vehicle identification number

        Returns:
            Doors and windows status
        """
        response = self._make_request(
            "GET", f"/connected-vehicle/v2/vehicles/{vin}/doors"
        )
        return response.get("data", {})

    def get_windows_status(self, vin: str) -> Dict[str, Any]:
        """
        Get windows status

        Args:
            vin: Vehicle identification number

        Returns:
            Windows status information
        """
        response = self._make_request(
            "GET", f"/connected-vehicle/v2/vehicles/{vin}/windows"
        )
        return response.get("data", {})

    def get_brake_fluid_status(self, vin: str) -> Dict[str, Any]:
        """
        Get brake fluid status

        Args:
            vin: Vehicle identification number

        Returns:
            Brake fluid status
        """
        response = self._make_request(
            "GET", f"/connected-vehicle/v2/vehicles/{vin}/brake-fluid"
        )
        return response.get("data", {})

    def get_washer_fluid_status(self, vin: str) -> Dict[str, Any]:
        """
        Get washer fluid status

        Args:
            vin: Vehicle identification number

        Returns:
            Washer fluid status
        """
        response = self._make_request(
            "GET", f"/connected-vehicle/v2/vehicles/{vin}/washer-fluid"
        )
        return response.get("data", {})

    def get_tyre_status(self, vin: str) -> Dict[str, Any]:
        """
        Get tyre pressure and status

        Args:
            vin: Vehicle identification number

        Returns:
            Tyre status information
        """
        response = self._make_request(
            "GET", f"/connected-vehicle/v2/vehicles/{vin}/tyres"
        )
        return response.get("data", {})

    # Command methods (require appropriate permissions)

    def lock_vehicle(self, vin: str) -> Dict[str, Any]:
        """
        Lock the vehicle

        Args:
            vin: Vehicle identification number

        Returns:
            Command result
        """
        response = self._make_request(
            "POST", f"/connected-vehicle/v2/vehicles/{vin}/commands/lock"
        )
        return response.get("data", {})

    def unlock_vehicle(self, vin: str) -> Dict[str, Any]:
        """
        Unlock the vehicle

        Args:
            vin: Vehicle identification number

        Returns:
            Command result
        """
        response = self._make_request(
            "POST", f"/connected-vehicle/v2/vehicles/{vin}/commands/unlock"
        )
        return response.get("data", {})

    def start_engine(self, vin: str, runtime_minutes: int = 15) -> Dict[str, Any]:
        """
        Start the engine remotely (if supported)

        Args:
            vin: Vehicle identification number
            runtime_minutes: How long to run the engine

        Returns:
            Command result
        """
        json_data = {"runtime": runtime_minutes}
        response = self._make_request(
            "POST",
            f"/connected-vehicle/v2/vehicles/{vin}/commands/engine-start",
            json_data=json_data,
        )
        return response.get("data", {})

    def stop_engine(self, vin: str) -> Dict[str, Any]:
        """
        Stop the engine remotely (if supported)

        Args:
            vin: Vehicle identification number

        Returns:
            Command result
        """
        response = self._make_request(
            "POST", f"/connected-vehicle/v2/vehicles/{vin}/commands/engine-stop"
        )
        return response.get("data", {})

    def start_climate(
        self, vin: str, temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Start climate control

        Args:
            vin: Vehicle identification number
            temperature: Target temperature in Celsius

        Returns:
            Command result
        """
        json_data = {}
        if temperature is not None:
            json_data["temperature"] = temperature

        response = self._make_request(
            "POST",
            f"/connected-vehicle/v2/vehicles/{vin}/commands/climatization-start",
            json_data=json_data,
        )
        return response.get("data", {})

    def stop_climate(self, vin: str) -> Dict[str, Any]:
        """
        Stop climate control

        Args:
            vin: Vehicle identification number

        Returns:
            Command result
        """
        response = self._make_request(
            "POST", f"/connected-vehicle/v2/vehicles/{vin}/commands/climatization-stop"
        )
        return response.get("data", {})
