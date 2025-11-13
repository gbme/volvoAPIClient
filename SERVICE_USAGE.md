# Volvo API Service Documentation

## Overview

The `VolvoAPIService` is a production-ready service for integrating Volvo Cars API into your applications. It handles authentication, token management, rate limiting, caching, and background data collection.

## Features

- ✅ **Automatic Authentication**: Handles OAuth2 + PKCE with token refresh
- ✅ **Rate Limiting**: Respects API rate limits automatically  
- ✅ **Caching**: Configurable response caching to reduce API calls
- ✅ **Background Collection**: Scheduled data collection with callbacks
- ✅ **Error Handling**: Comprehensive error handling and retry logic
- ✅ **Data Persistence**: Automatic data saving and cleanup
- ✅ **Production Ready**: Logging, threading, and proper resource management

## Quick Start

### 1. Basic Usage

```python
from volvo_service import VolvoAPIService

# Initialize service
service = VolvoAPIService()

# One-time authentication setup
if not service.authenticate_if_needed():
    service.setup_authentication()

# Get vehicle data
vehicles = service.get_vehicles()
for vehicle in vehicles:
    vin = vehicle['vin']
    data = service.get_vehicle_data(vin)
    print(f"Vehicle {vin}: {data}")
```

### 2. Background Data Collection

```python
import logging
from volvo_service import VolvoAPIService

# Setup logging
logging.basicConfig(level=logging.INFO)

# Initialize service
service = VolvoAPIService(cache_duration_minutes=10)

# Authentication
if not service.authenticate_if_needed():
    service.setup_authentication()

# Register callback for alerts
def low_battery_alert(vin: str, data: dict):
    fuel_data = data.get('fuel_status', {})
    battery = fuel_data.get('batteryChargeLevel', {}).get('value', 0)
    if battery < 20:
        print(f"🔋 LOW BATTERY: {vin} at {battery}%")

service.register_data_callback("alerts", low_battery_alert)

# Start background collection every 15 minutes
service.start_background_collection(interval_minutes=15)

# Keep running
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    service.stop_background_collection()
```

## Configuration

The service uses your existing `.env` file:

```bash
# Required
VOLVO_CLIENT_ID=your_client_id
VOLVO_CLIENT_SECRET=your_client_secret  
VOLVO_REDIRECT_URI=http://localhost:8080/volvo
VOLVO_VCC_API_KEY=your_vcc_api_key

# Optional scopes
VOLVO_SCOPES=conve:attributes,conve:fuel_status,conve:warnings
```

## Service Configuration

```python
service = VolvoAPIService(
    config_path=".env",                    # Path to config file
    data_dir="data",                       # Data storage directory
    token_file="tokens.json",              # Token storage file
    cache_duration_minutes=5               # Cache response duration
)
```

## API Methods

### Vehicle Management
- `get_vehicles()` - Get list of all vehicles
- `get_vehicle_data(vin)` - Get comprehensive vehicle data
- `load_latest_vehicle_data(vin)` - Load most recent saved data

### Data Collection  
- `collect_all_vehicles_data()` - Collect data for all vehicles
- `save_vehicle_data(vin, data)` - Save data to file
- `register_data_callback(name, callback)` - Register data callback

### Background Service
- `start_background_collection(interval_minutes)` - Start scheduled collection
- `stop_background_collection()` - Stop background service
- `cleanup_old_files(days_to_keep)` - Clean up old data files

## Architecture Patterns

### 1. Web Application Integration

```python
from flask import Flask, jsonify
from volvo_service import VolvoAPIService

app = Flask(__name__)
service = VolvoAPIService()

@app.route('/vehicles')
def vehicles():
    try:
        vehicles = service.get_vehicles()
        return jsonify(vehicles)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/vehicle/<vin>/status')
def vehicle_status(vin):
    try:
        data = service.get_vehicle_data(vin)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Setup authentication once
    if not service.authenticate_if_needed():
        service.setup_authentication()
    
    app.run(debug=True)
```

### 2. Microservice Integration

```python
import asyncio
from volvo_service import VolvoAPIService

class VehicleDataService:
    def __init__(self):
        self.volvo_service = VolvoAPIService()
        
    async def start_service(self):
        """Initialize the service"""
        if not self.volvo_service.authenticate_if_needed():
            raise RuntimeError("Authentication required")
        
        # Setup callbacks
        self.volvo_service.register_data_callback("processor", self.process_data)
        
        # Start background collection  
        self.volvo_service.start_background_collection(interval_minutes=10)
        
    def process_data(self, vin: str, data: dict):
        """Process incoming vehicle data"""
        # Send to message queue, database, etc.
        pass
        
    async def get_vehicle_status(self, vin: str) -> dict:
        """Get latest vehicle status"""
        return self.volvo_service.get_vehicle_data(vin)
```

### 3. Database Integration

```python
import sqlite3
import json
from volvo_service import VolvoAPIService

class VehicleDatabase:
    def __init__(self, db_path="vehicles.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.setup_tables()
        
        # Initialize Volvo service
        self.service = VolvoAPIService()
        self.service.register_data_callback("database", self.store_data)
    
    def setup_tables(self):
        """Create database tables"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vehicle_data (
                id INTEGER PRIMARY KEY,
                vin TEXT NOT NULL,
                collected_at TEXT NOT NULL,
                data TEXT NOT NULL
            )
        """)
        self.conn.commit()
    
    def store_data(self, vin: str, data: dict):
        """Store vehicle data in database"""
        self.conn.execute(
            "INSERT INTO vehicle_data (vin, collected_at, data) VALUES (?, ?, ?)",
            (vin, data.get('collected_at'), json.dumps(data))
        )
        self.conn.commit()
    
    def get_latest_data(self, vin: str) -> dict:
        """Get latest data for vehicle from database"""
        cursor = self.conn.execute(
            "SELECT data FROM vehicle_data WHERE vin = ? ORDER BY collected_at DESC LIMIT 1",
            (vin,)
        )
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
```

## Authentication Flow

### Initial Setup (One-time)
1. Call `setup_authentication()` 
2. Follow the interactive authentication flow
3. Tokens are automatically saved for future use

### Automatic Operation
- Service automatically checks token validity
- Refreshes tokens when needed
- No manual intervention required

## Error Handling

The service includes comprehensive error handling:

```python
from volvo_api import AuthenticationError, VolvoAPIError

try:
    data = service.get_vehicle_data(vin)
except AuthenticationError:
    # Re-authentication required
    service.setup_authentication()
except VolvoAPIError as e:
    # API-specific error (rate limit, permissions, etc.)
    print(f"API Error: {e}")
except Exception as e:
    # Unexpected error
    print(f"Unexpected error: {e}")
```

## Monitoring and Logging

Enable comprehensive logging:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('volvo_api.log'),
        logging.StreamHandler()
    ]
)
```

## Performance Optimization

### Caching Strategy
- API responses are cached for configurable duration
- Reduces redundant API calls
- Automatic cache invalidation

### Rate Limiting
- Automatic rate limit compliance
- Configurable minimum request intervals
- Prevents API throttling

### Background Processing
- Non-blocking data collection
- Threaded execution
- Graceful shutdown handling

## Deployment Considerations

### Docker Integration
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "app_example.py"]
```

### Environment Variables
```bash
# Production settings
VOLVO_CLIENT_ID=prod_client_id
VOLVO_CLIENT_SECRET=prod_secret
VOLVO_VCC_API_KEY=prod_api_key
VOLVO_REDIRECT_URI=https://yourdomain.com/callback
```

### Scaling
- Service is thread-safe for read operations
- Use separate instances for high-throughput scenarios
- Consider connection pooling for database integration

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Check client ID/secret in .env file
   - Verify redirect URI matches Volvo Developer Portal
   - Ensure VCC API key is correct

2. **API Rate Limits**  
   - Service automatically handles rate limiting
   - Increase cache duration to reduce API calls
   - Monitor logs for rate limit warnings

3. **Insufficient Permissions**
   - Check scopes in Volvo Developer Portal
   - Update VOLVO_SCOPES in .env file
   - Some endpoints require additional permissions

4. **Token Expiration**
   - Service automatically refreshes tokens
   - Check token storage file permissions
   - Verify refresh token is valid

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.getLogger('volvo_service').setLevel(logging.DEBUG)
```

## Best Practices

1. **Authentication**: Set up authentication once, let service handle token refresh
2. **Caching**: Use appropriate cache duration based on data freshness needs
3. **Error Handling**: Always wrap API calls in try/catch blocks
4. **Monitoring**: Enable logging and monitor for API errors
5. **Cleanup**: Regularly clean up old data files
6. **Rate Limits**: Respect API rate limits with appropriate intervals
7. **Security**: Keep credentials secure, use environment variables