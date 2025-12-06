# ParcelApp Integration - Developer Guide

## File Structure

```
custom_components/parcelapp/
├── __init__.py              # Setup, unload, device cleanup
├── api.py                   # ParcelApp API client
├── config_flow.py           # Configuration UI flow
├── const.py                 # Constants and defaults
├── coordinator.py           # Data update coordinator
├── sensor.py                # Sensor platform
├── manifest.json            # Integration metadata
├── strings.json             # UI strings
└── translations/en.json     # English translations
```

## How It Works

### 1. Setup Flow
1. User enters API key via config flow
2. Key is validated against ParcelApp API
3. Integration is created and stored securely
4. DataUpdateCoordinator starts polling

### 2. Update Cycle (Every Poll Interval)
1. Coordinator calls `api.get_deliveries()`
2. Response is parsed and stored in `coordinator.data`
3. Sensors are created/updated for each delivery
4. Cleanup task checks for deliveries to remove (status_code=0, 3+ days old)
5. Devices are removed from registry as needed

### 3. Automatic Cleanup
- Runs every update cycle
- Removes devices where:
  - `status_code == 0` (completed)
  - `date_expected >= 3 days ago`
- Uses Home Assistant device registry

## API Reference

### Get Deliveries

```python
from custom_components.parcelapp.api import ParcelAppAPI

api = ParcelAppAPI(api_key)
result = await api.get_deliveries(filter_mode="active")
```

**Parameters:**
- `filter_mode` (optional): "active" or "recent" (default: "recent")

**Response:**
```json
{
  "success": true,
  "deliveries": [
    {
      "tracking_number": "028-1259128-3671508",
      "carrier_code": "amzlde",
      "description": "Package Description",
      "status_code": 2,
      "date_expected": "2025-12-06 00:00:00",
      "date_expected_end": "2025-12-08 00:00:00",
      "events": [
        {
          "event": "Package departed facility",
          "date": "Saturday, 6 December 1:21 am",
          "location": "Florstadt, Hesse DE"
        }
      ],
      "extra_information": "UJ0nZmRFZ"
    }
  ]
}
```

### Add Delivery

```python
result = await api.add_delivery(
    tracking_number="12345",
    carrier_code="pholder",
    description="My Package",
    send_push_confirmation=False
)
```

**Parameters:**
- `tracking_number` (required): Tracking number
- `carrier_code` (required): Carrier code (use "pholder" for placeholder)
- `description` (required): Human-readable description
- `language` (optional): ISO 639-1 language code (default: "en")
- `send_push_confirmation` (optional): Send push notification (default: false)

**Response:**
```json
{
  "success": true
}
```

or

```json
{
  "success": false,
  "error_message": "Error description"
}
```

## Key Classes

### ParcelAppAPI (api.py)
- `get_deliveries(filter_mode)` - Fetch deliveries
- `add_delivery(...)` - Add new delivery
- Async/await support with aiohttp
- Error handling and logging

### ParcelAppCoordinator (coordinator.py)
- Extends DataUpdateCoordinator
- Polls API at configured interval
- Parses response data
- Marks deliveries for cleanup
- Maps status codes to names

### ParcelAppSensor (sensor.py)
- Extends SensorEntity
- Creates device per parcel
- Sets sensor attributes
- Integrates with device registry

## Configuration Options

### Setup (One-time)
- **API Key** (required): ParcelApp Premium account API key
- Validated against ParcelApp API

### Runtime Options
- **Poll Interval** (optional): Seconds between API calls (default: 300)
- **Filter Mode** (optional): "active" or "recent" (default: "active")

## Testing

### Test API Connectivity

```bash
python test_api.py
```

Returns: 10 active deliveries from your account with full response structure

## Rate Limiting

ParcelApp API limits:
- GET /deliveries/: 20 requests per hour
- POST /add-delivery/: 20 requests per day

Default 5-minute poll interval (300 seconds) = 12 requests/hour ✅

Safe minimum: 180 seconds (3 minutes) = 20 requests/hour

## Sensor Attributes

Each tracking sensor includes:

| Attribute | Type | Description |
|-----------|------|-------------|
| tracking_number | string | Parcel tracking number |
| carrier | string | Carrier code (amzlde, dp, gls, etc.) |
| description | string | Parcel description |
| status_code | integer | Numeric status (0-8) |
| date_expected | string | Expected delivery date |
| date_expected_end | string | End of delivery window |
| latest_event | string | Most recent tracking event |
| latest_location | string | Last known location |
| extra_information | string | Postcode, email, or notes |

## Device Registry Integration

Devices are created with:
- **Unique ID**: `("parcelapp", tracking_number)`
- **Name**: Parcel description or tracking number
- **Manufacturer**: ParcelApp
- **Model**: Carrier code
- **Entry**: Integration entry

## Extending the Integration

### Add a New Service

```python
# In __init__.py

async def async_setup_entry(hass, entry):
    hass.services.async_register(
        DOMAIN,
        "service_name",
        handle_service,
        schema=vol.Schema({...})
    )
```

### Add a New Platform

1. Create `new_platform.py` in `custom_components/parcelapp/`
2. Implement async_setup_platform()
3. Add to manifest.json
4. Update strings.json

### Add Configuration Options

1. Add to config_flow.py options_schema
2. Store in coordinator
3. Update const.py with new default

## Debugging

Enable debug logging:

```yaml
logger:
  logs:
    custom_components.parcelapp: debug
```

Common issues:
- **Invalid API key**: Check configuration
- **Rate limited**: Increase poll interval
- **No devices**: Check ParcelApp account has deliveries
- **Devices not updating**: Check Home Assistant logs for errors

## Dependencies

- **aiohttp**: Async HTTP client
- **python-dateutil**: Date parsing
- Home Assistant core libraries (DataUpdateCoordinator, SensorEntity, etc.)

No external package requirements beyond Home Assistant base.

## Version History

- **1.0.0**: Initial release
  - Device creation per parcel
  - Real-time tracking
  - Automatic cleanup (3-day threshold)
  - HACS support
  - Full ParcelApp API integration
