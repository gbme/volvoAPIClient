#!/usr/bin/env python3
"""
Volvo Battery Monitor - MQTT Publisher

This script:
1. Gets battery charge level for multiple Volvo vehicles
2. Sends the data via MQTT HTTP API every 5 minutes
3. Includes comprehensive logging and error handling
4. Can be run as a cron job or systemd service
5. Supports multiple VINs (configured in TARGET_VINS or via --vins argument)

Usage:
    # Run once for all configured VINs
    python volvo_battery_mqtt.py

    # Run for specific VINs
    python volvo_battery_mqtt.py --vins "VIN1,VIN2,VIN3"

    # Run in background loop (every 5 minutes)
    python volvo_battery_mqtt.py --loop

    # Test mode (run once with debug output)
    python volvo_battery_mqtt.py --test

    # First-time authentication setup
    python volvo_battery_mqtt.py --auth
"""

import argparse
import json
import logging
import math
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# Add current directory to path for imports
sys.path.append(".")

from volvo_api import VolvoAPIClient, VolvoAuth
from volvo_api.config import VolvoConfig


class VolvoBatteryMQTTPublisher:
    """Volvo Battery Level MQTT Publisher"""

    # Configuration - Add your vehicle VINs here
    TARGET_VINS = [
        "YV1XZEFV9P2111126",  # Replace with your actual VIN(s)
        "YV1LFBABDJ1371367",  # Second vehicle VIN
        # Add more VINs here as needed:
        # "YV1XZEFV9P2222222",  # Second vehicle VIN
        # "YV1XZEFV9P3333333",  # Third vehicle VIN
        # "WVWZZZ3CZKE123456",  # Example: Another Volvo VIN format
    ]
    
    # Home location configuration (replace with your actual home coordinates)
    HOME_LATITUDE = 52.21389700028309  # Replace with your home latitude
    HOME_LONGITUDE = 5.179792579410594  # Replace with your home longitude
    HOME_RADIUS_METERS = 100  # Radius in meters to consider as "home"
    
    MQTT_API_URL = (
        "http://192.168.1.200:15672/api/exchanges/gbme_vhost/gbme_exchange/publish"
    )

    def __init__(self, test_mode=False, test_auth=False, vins=None):
        """Initialize the publisher

        Args:
            test_mode: Enable test mode (no MQTT publishing)
            test_auth: Show curl commands for debugging
            vins: List of VINs to monitor (overrides default TARGET_VINS)
        """
        self.test_mode = test_mode
        self.test_auth = test_auth

        # Use provided VINs or fall back to default
        self.TARGET_VINS = vins if vins is not None else self.TARGET_VINS

        self.setup_logging()
        self.logger = logging.getLogger(__name__)

        # Log which VINs will be monitored
        self.logger.info(
            "📋 Configured to monitor %d vehicle(s): %s",
            len(self.TARGET_VINS),
            ", ".join(self.TARGET_VINS),
        )

        # Initialize Volvo API
        try:
            self.config = VolvoConfig()
            self.auth = VolvoAuth(
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
                redirect_uri=self.config.redirect_uri,
                scopes=self.config.DEFAULT_SCOPES,
                use_pkce=True,
                token_storage_path="tokens.json",
            )
            self.client = VolvoAPIClient(
                auth=self.auth, vcc_api_key=self.config.vcc_api_key
            )
            self.logger.info("✅ Volvo API client initialized")
        except Exception as e:
            self.logger.error("❌ Failed to initialize Volvo API: %s", str(e))
            raise

    def setup_logging(self):
        """Setup logging configuration"""
        log_level = logging.DEBUG if self.test_mode else logging.INFO
        log_format = "%(asctime)s - %(levelname)s - %(message)s"

        # Create logs directory
        Path("logs").mkdir(exist_ok=True)

        # Configure logging
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler("logs/volvo_battery_mqtt.log"),
                logging.StreamHandler(sys.stdout),
            ],
        )

    def get_battery_and_charging_data(self, vin: str) -> dict:
        """
        Get battery charge level and charging information for the specified VIN

        Args:
            vin: Vehicle identification number

        Returns:
            Dictionary with battery and charging information or error details
        """
        try:
            self.logger.info("🔋 Getting battery and charging data for VIN: %s", vin)

            # Check authentication
            if not self.auth.is_authenticated():
                self.logger.error("❌ Authentication required - tokens may be expired")
                self.logger.error(
                    "💡 To authenticate for the first time, run: python authenticate.py"
                )
                return {
                    "error": "authentication_required",
                    "message": "No valid authentication. Run 'python authenticate.py' to set up authentication.",
                }

            # Initialize result structure
            result = {
                "vin": vin,
                "timestamp": datetime.now().isoformat(),
                "battery_level": None,
                "unit": "%",
                "updated_at": None,
                "charging_status": None,
                "charging_current": None,
                "charging_power": None,
                "charger_connected": None,
                "charging_type": None,
                "source": None,
                # Location data
                "location": {
                    "latitude": None,
                    "longitude": None,
                    "heading": None,
                    "speed": None,
                    "updated_at": None,
                    "status": None,
                },
            }

            # Try energy state first (Energy API v2) - comprehensive data
            energy_data_available = False
            try:
                # Generate curl commands if test_auth is enabled
                if self.test_auth:
                    self._generate_curl_commands(vin)

                self.logger.debug("Attempting Energy API v2...")
                energy_state = self.client.get_energy_state(vin)
                self.logger.debug("Energy state response: %s", energy_state)

                if energy_state:
                    # Extract battery level
                    battery_info = energy_state.get("batteryChargeLevel", {})
                    if battery_info.get("status") == "OK":
                        result["battery_level"] = battery_info.get("value")
                        result["updated_at"] = battery_info.get("updatedAt")
                        result["unit"] = battery_info.get("unit", "%")
                        energy_data_available = True
                        result["source"] = "energy_api_v2"

                    # Extract charging status
                    charging_status_info = energy_state.get("chargingStatus", {})
                    if charging_status_info.get("status") == "OK":
                        result["charging_status"] = charging_status_info.get("value")

                    # Extract charging current limit
                    charging_current_info = energy_state.get("chargingCurrentLimit", {})
                    if charging_current_info.get("status") == "OK":
                        result["charging_current"] = charging_current_info.get("value")

                    # Extract charging power
                    charging_power_info = energy_state.get("chargingPower", {})
                    if charging_power_info.get("status") == "OK":
                        result["charging_power"] = charging_power_info.get("value")

                    # Extract charger connection status
                    connection_info = energy_state.get("chargerConnectionStatus", {})
                    if connection_info.get("status") == "OK":
                        result["charger_connected"] = connection_info.get("value")

                    # Extract charging type
                    charging_type_info = energy_state.get("chargingType", {})
                    if charging_type_info.get("status") == "OK":
                        result["charging_type"] = charging_type_info.get("value")
                    # Extract charging type
                    charging_limit_info = energy_state.get("chargingCurrentLimit", {})
                    if charging_limit_info.get("status") == "OK":
                        result["charging_limit"] = charging_limit_info.get("value")

                    if energy_data_available:
                        self.logger.info(
                            "✅ Data retrieved from Energy API v2: battery=%s%s, charging_status=%s",
                            result["battery_level"],
                            result["unit"],
                            result["charging_status"],
                        )
                        # Get location and enrichment data before returning
                        self._get_location_data(result, vin)
                        self._enrich_charging_data(result, vin)
                        return result

            except Exception as e:
                self.logger.warning(
                    "⚠️ Energy API v2 failed: %s, trying fuel status API", str(e)
                )

            # Fallback to fuel status endpoint for battery level
            if not energy_data_available:
                try:
                    self.logger.debug("Attempting fuel status API for battery level...")
                    fuel_status = self.client.get_fuel_status(vin)
                    self.logger.debug("Fuel status response: %s", fuel_status)

                    # Extract battery level from fuel status
                    battery_info = fuel_status.get("batteryChargeLevel", {})

                    if battery_info and "value" in battery_info:
                        result["battery_level"] = battery_info.get("value")
                        result["updated_at"] = battery_info.get(
                            "timestamp", datetime.now().isoformat()
                        )
                        result["unit"] = battery_info.get("unit", "%")
                        result["source"] = "fuel_status_api"

                        self.logger.info(
                            "✅ Battery level retrieved from fuel status API: %s%s",
                            result["battery_level"],
                            result["unit"],
                        )
                    else:
                        self.logger.error(
                            "❌ No battery data in fuel status response: %s",
                            fuel_status,
                        )
                        return {
                            "error": "no_battery_data",
                            "message": "No battery information available in fuel status",
                            "vin": vin,
                            "timestamp": datetime.now().isoformat(),
                        }

                except Exception as fuel_error:
                    self.logger.error("❌ Fuel status API failed: %s", str(fuel_error))
                    return {
                        "error": "api_failure",
                        "message": f"All API endpoints failed. Fuel API error: {str(fuel_error)}",
                        "vin": vin,
                        "timestamp": datetime.now().isoformat(),
                    }

            # Try to get location information
            self._get_location_data(result, vin)

            # Try to get additional charging information from other endpoints
            self._enrich_charging_data(result, vin)

            return result

        except Exception as e:
            self.logger.error(
                "❌ Unexpected error getting battery and charging data: %s", str(e)
            )
            return {
                "error": "unexpected_error",
                "message": str(e),
                "vin": vin,
                "timestamp": datetime.now().isoformat(),
            }

    def _enrich_charging_data(self, result: dict, vin: str):
        """
        Try to get additional charging information from other endpoints

        Args:
            result: Dictionary to enrich with charging data
            vin: Vehicle identification number
        """
        try:
            # Try to get engine status (might have charging info)
            try:
                self.logger.debug(
                    "Attempting to get engine status for charging data..."
                )
                engine_status = self.client.get_engine_status(vin)
                print(engine_status)
                self.logger.debug("Engine status response: %s", engine_status)

                # Look for any charging-related fields in engine status
                # (This is speculative - actual field names may vary)
                if engine_status and isinstance(engine_status, dict):
                    for key, value in engine_status.items():
                        if "charg" in key.lower():
                            self.logger.debug(
                                "Found charging-related field in engine status: %s = %s",
                                key,
                                value,
                            )

            except Exception as e:
                self.logger.debug("Engine status API unavailable: %s", str(e))

            # For now, if we don't have charging status, infer it from battery level and time
            if result.get("charging_status") is None:
                battery_level = result.get("battery_level")
                if battery_level is not None:
                    if battery_level >= 95:
                        result["charging_status"] = (
                            "IDLE"  # Likely not charging if nearly full
                        )
                    else:
                        result["charging_status"] = (
                            "UNKNOWN"  # Cannot determine without more data
                        )

            # Set default values for missing charging data
            if result.get("charging_current") is None:
                result["charging_current"] = "N/A"
            if result.get("charging_power") is None:
                result["charging_power"] = "N/A"
            if result.get("charger_connected") is None:
                result["charger_connected"] = "UNKNOWN"
            if result.get("charging_type") is None:
                result["charging_type"] = "N/A"

        except Exception as e:
            self.logger.debug("Error enriching charging data: %s", str(e))

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the distance between two GPS coordinates using the Haversine formula
        
        Args:
            lat1, lon1: First coordinate pair (latitude, longitude)
            lat2, lon2: Second coordinate pair (latitude, longitude)
            
        Returns:
            Distance in meters
        """
        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        # Earth's radius in meters
        earth_radius_m = 6371000
        
        # Distance in meters
        distance = earth_radius_m * c
        return distance

    def _is_at_home(self, latitude: float, longitude: float) -> bool:
        """
        Check if the given coordinates are within the home radius
        
        Args:
            latitude: Vehicle latitude
            longitude: Vehicle longitude
            
        Returns:
            True if within home radius, False otherwise
        """
        distance = self._calculate_distance(
            latitude, longitude, 
            self.HOME_LATITUDE, self.HOME_LONGITUDE
        )
        return distance <= self.HOME_RADIUS_METERS

    def _get_location_data(self, result: dict, vin: str):
        """
        Get vehicle location information

        Args:
            result: Dictionary to enrich with location data
            vin: Vehicle identification number
        """
        try:
            self.logger.info("🌍 Attempting to get location data for VIN: %s", vin)
            location_data = self.client.get_location(vin)
            self.logger.debug("Location response: %s", location_data)

            if location_data and isinstance(location_data, dict):
                # Extract location coordinates
                geometry = location_data.get("geometry", {})
                if geometry and "coordinates" in geometry:
                    coordinates = geometry["coordinates"]
                    if len(coordinates) >= 2:
                        result["location"]["longitude"] = coordinates[0]
                        result["location"]["latitude"] = coordinates[1]

                # Extract location properties
                properties = location_data.get("properties", {})
                if properties:
                    result["location"]["heading"] = properties.get("heading")
                    result["location"]["speed"] = properties.get("speed")
                    result["location"]["updated_at"] = properties.get("timestamp")
                    result["location"]["status"] = "OK"

                    # Check if vehicle is at home
                    lat = result["location"]["latitude"]
                    lon = result["location"]["longitude"]
                    
                    if lat is not None and lon is not None and self._is_at_home(lat, lon):
                        # Vehicle is at home - simplify location data
                        distance_to_home = self._calculate_distance(lat, lon, self.HOME_LATITUDE, self.HOME_LONGITUDE)
                        
                        result["location"] = {
                            "location": "home",
                            "distance_from_home": round(distance_to_home, 1),
                            "heading": properties.get("heading"),
                            "updated_at": properties.get("timestamp"),
                            "status": "OK"
                        }
                        
                        self.logger.info(
                            "✅ [%s] Location: 🏠 home (%.1fm from center), heading=%s°",
                            vin,
                            distance_to_home,
                            result["location"]["heading"] or "N/A"
                        )
                    else:
                        # Vehicle is away from home - keep detailed coordinates
                        self.logger.info(
                            "✅ [%s] Location retrieved: lat=%.6f, lon=%.6f, heading=%s°",
                            vin,
                            lat or 0,
                            lon or 0,
                            result["location"]["heading"] or "N/A"
                        )
                else:
                    self.logger.debug("No location properties found in response")
                    result["location"]["status"] = "NO_DATA"
            else:
                self.logger.debug("No location data available")
                result["location"]["status"] = "NO_DATA"

        except Exception as e:
            self.logger.debug("Location API failed: %s", str(e))
            result["location"]["status"] = "ERROR"
            result["location"]["error"] = str(e)

    def publish_to_mqtt(self, data: dict) -> bool:
        """
        Publish data to MQTT via HTTP API

        Args:
            data: Dictionary containing battery data or error information

        Returns:
            True if published successfully, False otherwise
        """
        try:
            # Get VIN from data for routing key
            vin = data.get("vin", "UNKNOWN")

            # Prepare MQTT message
            mqtt_message = {
                "properties": {},
                "routing_key": f"volvo.car.{vin}",
                "payload": json.dumps(data),
                "payload_encoding": "string",
            }

            self.logger.info(
                "📡 Publishing to MQTT: routing_key=%s", mqtt_message["routing_key"]
            )

            if self.test_mode:
                self.logger.info(
                    "🧪 TEST MODE - Would publish: %s",
                    json.dumps(mqtt_message, indent=2),
                )
                return True

            # Make HTTP POST request to MQTT API with proper headers
            headers = {
                "Authorization": "Basic Z2JtZTpwYXNz",
                "Content-Type": "application/json",
            }

            response = requests.post(
                self.MQTT_API_URL,
                json=mqtt_message,
                headers=headers,
                timeout=10,
            )

            if response.status_code in [200, 201]:
                self.logger.info("✅ Successfully published to MQTT")
                return True
            else:
                self.logger.error(
                    "❌ MQTT publish failed: HTTP %s - %s",
                    response.status_code,
                    response.text,
                )
                return False

        except requests.exceptions.RequestException as e:
            self.logger.error("❌ Network error publishing to MQTT: %s", str(e))
            return False
        except Exception as e:
            self.logger.error("❌ Unexpected error publishing to MQTT: %s", str(e))
            return False

    def _generate_curl_commands(self, vin):
        """Generate curl commands for debugging API calls"""
        if not self.client or not hasattr(self.client, "auth"):
            print("❌ No authenticated client available for curl generation")
            return

        token = self.client.auth.get_access_token()
        if not token:
            print("❌ No access token available for curl generation")
            return

        # Base curl command with authentication
        base_curl = f'curl -X GET \\\n  -H "Authorization: Bearer {token}" \\\n  -H "VCC-Api-Key: {self.client.vcc_api_key}" \\\n  -H "Content-Type: application/json"'

        print("\n🔍 DEBUG: Equivalent curl commands for API calls:")
        print("=" * 60)

        # Energy API v2 endpoints
        print("\n1. Energy State API:")
        energy_url = f"https://api.volvocars.com/energy/v2/vehicles/{vin}"
        print(f'{base_curl} \\\n  "{energy_url}"')

        print("\n2. Energy Capabilities API:")
        capabilities_url = (
            f"https://api.volvocars.com/energy/v2/vehicles/{vin}/capabilities"
        )
        print(f'{base_curl} \\\n  "{capabilities_url}"')

        # Fallback fuel status API
        print("\n3. Fuel Status API (fallback):")
        fuel_url = f"https://api.volvocars.com/connected-vehicle/v2/vehicles/{vin}/fuel"
        print(f'{base_curl} \\\n  "{fuel_url}"')

        # Location API
        print("\n4. Location API:")
        location_url = f"https://api.volvocars.com/location/v1/vehicles/{vin}/location"
        print(f'{base_curl} \\\n  "{location_url}"')

        print("\n" + "=" * 60)
        print(
            "Note: Replace the bearer token if it expires (tokens are valid for ~1 hour)"
        )
        print()

    def run_once(self) -> bool:
        """
        Run once: get battery level and publish to MQTT for all VINs

        Returns:
            True if all VINs processed successfully, False otherwise
        """
        self.logger.info(
            "🚗 Starting Volvo battery monitoring cycle for %d vehicles",
            len(self.TARGET_VINS),
        )

        overall_success = True

        for vin in self.TARGET_VINS:
            try:
                self.logger.info("🔍 Processing VIN: %s", vin)

                # Get battery and charging data for this VIN
                battery_data = self.get_battery_and_charging_data(vin)

                # Publish to MQTT
                success = self.publish_to_mqtt(battery_data)

                if success:
                    if "error" not in battery_data:
                        battery_level = battery_data.get("battery_level", "N/A")
                        unit = battery_data.get("unit", "")
                        charging_status = battery_data.get("charging_status", "N/A")
                        charging_power = battery_data.get("charging_power", "N/A")
                        
                        # Get location info for logging
                        location = battery_data.get("location", {})
                        location_status = location.get("status", "N/A")
                        
                        # Check if location is simplified to "home"
                        if location.get("location") == "home":
                            distance = location.get("distance_from_home", 0)
                            location_str = f"🏠 home ({distance}m)"
                        else:
                            # Traditional lat/lon format
                            lat = location.get("latitude")
                            lon = location.get("longitude")
                            
                            if lat is not None and lon is not None:
                                location_str = f"📍 {lat:.6f},{lon:.6f}"
                            else:
                                location_str = f"📍 {location_status}"

                        self.logger.info(
                            "✅ [%s] Completed - Battery: %s%s, Charging: %s, Power: %s, Location: %s",
                            vin,
                            battery_level,
                            unit,
                            charging_status,
                            charging_power,
                            location_str,
                        )
                    else:
                        self.logger.warning(
                            "⚠️ [%s] Completed with error data published", vin
                        )
                else:
                    self.logger.error("❌ [%s] Failed - could not publish to MQTT", vin)
                    overall_success = False

            except Exception as e:
                self.logger.error("❌ [%s] Failed with exception: %s", vin, str(e))
                overall_success = False

        self.logger.info(
            "🏁 Monitoring cycle completed for all %d vehicles", len(self.TARGET_VINS)
        )
        return overall_success

    def run_loop(self, interval_minutes: int = 5):
        """
        Run continuously every interval_minutes

        Args:
            interval_minutes: How often to run (default: 5 minutes)
        """
        self.logger.info(
            "🔄 Starting continuous monitoring (every %d minutes)", interval_minutes
        )
        interval_seconds = interval_minutes * 60

        try:
            while True:
                # Run monitoring cycle
                self.run_once()

                # Wait for next cycle
                self.logger.info(
                    "⏰ Waiting %d minutes until next cycle...", interval_minutes
                )
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            self.logger.info("👋 Received stop signal, shutting down gracefully")
        except Exception as e:
            self.logger.error("❌ Loop failed with exception: %s", str(e))
            raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Volvo Battery MQTT Publisher")
    parser.add_argument(
        "--loop", action="store_true", help="Run continuously every 5 minutes"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode - debug output, no actual MQTT publish",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Interval in minutes for loop mode (default: 5)",
    )
    parser.add_argument(
        "--test_auth",
        action="store_true",
        help="Show equivalent curl commands for debugging API authentication",
    )
    parser.add_argument(
        "--auth",
        action="store_true",
        help="Run initial authentication setup (same as running 'python authenticate.py')",
    )
    parser.add_argument(
        "--vins",
        type=str,
        help="Comma-separated list of VINs to monitor (overrides default list)",
    )

    args = parser.parse_args()

    # Handle authentication flag
    if args.auth:
        import subprocess

        print("🔐 Running authentication setup...")
        result = subprocess.run([sys.executable, "authenticate.py"], check=False)
        sys.exit(result.returncode)

    try:
        # Parse VINs from command line
        vins = None
        if args.vins:
            vins = [vin.strip() for vin in args.vins.split(",") if vin.strip()]
            print(f"📋 Using VINs from command line: {vins}")

        # Initialize publisher
        publisher = VolvoBatteryMQTTPublisher(
            test_mode=args.test, test_auth=args.test_auth, vins=vins
        )

        if args.loop:
            # Run continuously
            publisher.run_loop(interval_minutes=args.interval)
        else:
            # Run once
            success = publisher.run_once()
            sys.exit(0 if success else 1)

    except Exception as e:
        logging.error("❌ Application failed: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
