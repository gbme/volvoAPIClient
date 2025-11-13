# Volvo Cars API Client

A Python client library for the Volvo Cars API, providing easy access to vehicle data and remote commands through OAuth2 authentication.

## Features

- 🔐 **OAuth2 Authentication** - Complete implementation with PKCE support
- 🚗 **Vehicle Information** - Access detailed vehicle data (fuel, battery, odometer, etc.)
- 📊 **Real-time Status** - Get current status of doors, windows, engine, warnings
- 🎮 **Remote Commands** - Lock/unlock, start/stop engine, climate control
- 🔄 **Token Management** - Automatic token refresh and persistent storage
- ⚙️ **Configuration** - Environment-based configuration with validation
- 📝 **Type Hints** - Full type annotation support
- 🛡️ **Error Handling** - Comprehensive error handling and custom exceptions

## Installation

1. Clone this repository or copy the files to your project
2. Install required dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Get API Credentials

1. Visit the [Volvo Cars Developer Portal](https://developer.volvocars.com/)
2. Create an account and publish an application
3. Note your `client_id`, `client_secret`, and `redirect_uri`

### 2. Configure Environment

Copy the example environment file and add your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```bash
# Volvo Cars API credentials
VOLVO_CLIENT_ID=your_client_id_here
VOLVO_CLIENT_SECRET=your_client_secret_here
VOLVO_REDIRECT_URI=https://your-domain.com/callback
VOLVO_VIN=your_vehicle_vin_here  # Optional

# Optional: Override default URLs
VOLVO_API_BASE_URL=https://api.volvocars.com
VOLVO_AUTH_BASE_URL=https://volvoid.eu.volvocars.com
```

### 3. Run the Example

```bash
python example.py
```

The example script will guide you through:
- OAuth2 authentication flow
- Retrieving vehicle information
- Accessing various data endpoints

## Usage

### Basic Usage

```python
from volvo_api import VolvoAuth, VolvoAPIClient
from volvo_api.config import VolvoConfig

# Load configuration
config = VolvoConfig()

# Initialize authentication
auth = VolvoAuth(
    client_id=config.client_id,
    client_secret=config.client_secret,
    redirect_uri=config.redirect_uri,
    scopes=config.get_scopes_by_category("default")
)

# Authenticate (first time)
if not auth.is_authenticated():
    # Get authorization URL
    auth_url = auth.get_authorization_url()
    print(f"Visit: {auth_url}")
    
    # Get callback URL after user authorizes
    callback_url = input("Paste callback URL: ")
    code, state = VolvoAuth.extract_code_from_callback_url(callback_url)
    
    # Exchange code for tokens
    auth.exchange_code_for_tokens(code)

# Create API client
client = VolvoAPIClient(auth)

# Get vehicles
vehicles = client.get_vehicles()
vin = vehicles[0]["vin"]

# Get vehicle data
fuel_status = client.get_fuel_status(vin)
battery_level = client.get_battery_charge_level(vin)  # For electric/hybrid
odometer = client.get_odometer(vin)
warnings = client.get_warnings(vin)
```

### Available Data Endpoints

```python
# Vehicle information
vehicles = client.get_vehicles()
details = client.get_vehicle_details(vin)

# Status information
fuel = client.get_fuel_status(vin)
battery = client.get_battery_charge_level(vin)  # Electric/hybrid only
odometer = client.get_odometer(vin)
engine = client.get_engine_status(vin)
location = client.get_location(vin)  # If permitted

# Component status
doors = client.get_doors_status(vin)
windows = client.get_windows_status(vin)
tyres = client.get_tyre_status(vin)
brake_fluid = client.get_brake_fluid_status(vin)
washer_fluid = client.get_washer_fluid_status(vin)

# Warnings and diagnostics
warnings = client.get_warnings(vin)
```

### Remote Commands

```python
# Lock/unlock vehicle
client.lock_vehicle(vin)
client.unlock_vehicle(vin)

# Engine control (if supported)
client.start_engine(vin, runtime_minutes=15)
client.stop_engine(vin)

# Climate control
client.start_climate(vin, temperature=22.0)  # Temperature in Celsius
client.stop_climate(vin)
```

### Scope Categories

The library provides predefined scope categories for different use cases:

```python
config = VolvoConfig()

# Basic vehicle information only
basic_scopes = config.get_scopes_by_category("basic")

# Include remote commands
command_scopes = config.get_scopes_by_category("command")

# All available scopes
all_scopes = config.get_scopes_by_category("all")

# Default balanced set
default_scopes = config.get_scopes_by_category("default")
```

### Error Handling

```python
from volvo_api import (
    VolvoAPIError,
    AuthenticationError, 
    RateLimitError,
    VehicleNotFoundError
)

try:
    fuel_status = client.get_fuel_status(vin)
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    # Re-authenticate or refresh token
except RateLimitError as e:
    print(f"Rate limited: {e}")
    # Wait before retrying
except VehicleNotFoundError as e:
    print(f"Vehicle not found: {e}")
    # Check VIN or permissions
except VolvoAPIError as e:
    print(f"API error: {e}")
    print(f"Status code: {e.status_code}")
    print(f"Response: {e.response_data}")
```

## API Reference

### VolvoAuth

Main authentication class handling OAuth2 flow.

#### Methods

- `get_authorization_url(state=None)` - Generate authorization URL
- `exchange_code_for_tokens(code)` - Exchange authorization code for tokens
- `refresh_access_token()` - Refresh expired access token
- `get_access_token()` - Get valid access token (auto-refresh if needed)
- `is_authenticated()` - Check if authenticated with valid token
- `logout()` - Clear all tokens and authentication state

#### Static Methods

- `extract_code_from_callback_url(url)` - Extract code from OAuth callback URL

### VolvoAPIClient

Main API client for accessing Volvo Cars API endpoints.

#### Vehicle Information
- `get_vehicles()` - List all vehicles
- `get_vehicle_details(vin)` - Detailed vehicle information

#### Status Endpoints
- `get_fuel_status(vin)` - Fuel level and range
- `get_battery_charge_level(vin)` - Battery status (electric/hybrid)
- `get_odometer(vin)` - Odometer reading
- `get_engine_status(vin)` - Engine status and diagnostics
- `get_location(vin)` - Vehicle location (if permitted)

#### Component Status
- `get_doors_status(vin)` - Door open/closed status
- `get_windows_status(vin)` - Window status
- `get_tyre_status(vin)` - Tyre pressure
- `get_brake_fluid_status(vin)` - Brake fluid level
- `get_washer_fluid_status(vin)` - Washer fluid level
- `get_warnings(vin)` - Active warnings and alerts

#### Remote Commands
- `lock_vehicle(vin)` - Lock vehicle
- `unlock_vehicle(vin)` - Unlock vehicle
- `start_engine(vin, runtime_minutes=15)` - Start engine remotely
- `stop_engine(vin)` - Stop engine remotely
- `start_climate(vin, temperature=None)` - Start climate control
- `stop_climate(vin)` - Stop climate control

### Configuration

The `VolvoConfig` class manages configuration from environment variables:

```python
config = VolvoConfig(".env")  # Custom env file

# Check configuration
if not config.is_valid():
    missing = config.validate()
    print(f"Missing: {missing}")

# Get configuration values
client_id = config.client_id
scopes = config.get_scopes_by_category("command")
```

## Scopes and Permissions

Different API endpoints require different scopes (permissions). Here are the main scopes:

### Basic Scopes
- `openid` - Required for authentication
- `conve:vehicle_relation` - Access to vehicle list
- `conve:fuel_status` - Fuel level information
- `conve:battery_charge_level` - Battery status

### Advanced Scopes
- `conve:diagnostics_engine_status` - Engine diagnostics
- `conve:brake_status` - Brake system status
- `conve:warnings` - Vehicle warnings

### Command Scopes
- `conve:commands` - Basic remote commands
- `conve:lock_unlock` - Lock/unlock commands
- `conve:engine_start_stop` - Engine start/stop
- `conve:climatization_start_stop` - Climate control

## Project Structure

```
volvo_api/
├── __init__.py          # Package initialization
├── auth.py              # OAuth2 authentication
├── client.py            # Main API client
├── config.py            # Configuration management
└── exceptions.py        # Custom exceptions

example.py               # Complete usage example
requirements.txt         # Python dependencies
.env.example            # Environment template
.gitignore              # Git ignore rules
README.md               # This documentation
```

## Requirements

- Python 3.7+
- `requests` - HTTP library
- `python-dotenv` - Environment variable loading
- `pydantic` - Data validation (optional)

## Security Considerations

1. **Never commit secrets** - Use `.env` files and `.gitignore`
2. **Use PKCE** - Enabled by default for additional security
3. **Validate state parameter** - Prevent CSRF attacks
4. **Secure token storage** - Tokens are stored locally with restricted permissions
5. **HTTPS redirect URIs** - Always use HTTPS for production redirect URIs

## Troubleshooting

### Common Issues

1. **"No vehicles found"**
   - Ensure your Volvo ID account is linked to vehicles
   - Check that your application has the correct scopes
   - Verify the account used for authentication

2. **"Authentication failed"**
   - Check client ID and secret are correct
   - Ensure redirect URI matches exactly with registered URI
   - Verify scopes are properly configured

3. **"Rate limit exceeded"**
   - Implement proper backoff and retry logic
   - Monitor your API usage
   - Consider caching responses when appropriate

4. **"Vehicle not found"**
   - Verify VIN is correct
   - Check that the vehicle is accessible to your account
   - Ensure required scopes are granted

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is provided as-is for educational and development purposes. Please review Volvo Cars API terms of service for commercial usage.

## Links

- [Volvo Cars Developer Portal](https://developer.volvocars.com/)
- [API Documentation](https://developer.volvocars.com/apis/docs/)
- [OAuth2 Specification](https://datatracker.ietf.org/doc/html/rfc6749)
- [PKCE Specification](https://www.rfc-editor.org/rfc/rfc7636)# volvoAPIClient
