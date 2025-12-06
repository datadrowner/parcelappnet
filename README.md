# ParcelApp Home Assistant Integration

A Home Assistant HACS integration for tracking parcels through the ParcelApp API. Each parcel becomes a device with tracking sensors, and completed deliveries older than 3 days are automatically removed.

## Features

- **Per-Parcel Devices**: Each tracked parcel is a device in Home Assistant with carrier information
- **Real-Time Tracking**: Status sensors show delivery status and latest tracking events
- **Automatic Cleanup**: Completed deliveries older than 3 days are automatically removed
- **Configurable Polling**: Adjustable update interval (respects ParcelApp's rate limits)
- **Status Mapping**: Delivery statuses mapped to human-readable states (8 status codes)

## Installation

### HACS (Recommended)

1. Go to **HACS > Integrations**
2. Click **+ Explore & Download Repositories**
3. Search for "**ParcelApp**"
4. Click **Install**
5. Restart Home Assistant

Then configure in **Settings > Devices & Services > + Create Integration** and select **ParcelApp**.

### Manual Installation

1. Copy `custom_components/parcelapp/` to your Home Assistant `custom_components/` directory
2. Restart Home Assistant
3. Configure via **Settings > Devices & Services > + Create Integration**

## Getting Your API Key

1. Log in to https://web.parcelapp.net/
2. Go to API settings
3. Generate a new API key
4. Copy and paste into Home Assistant configuration

## Configuration

- **API Key** (required): Your ParcelApp Premium account API key
- **Poll Interval** (optional): Seconds between API calls (default: 300 = 5 minutes, range: 60-3600)
- **Filter Mode** (optional): "active" (currently tracking) or "recent" (includes completed)

## Status Codes

Delivery statuses are represented as numeric codes mapped to readable names:

| Code | Status | Meaning |
|------|--------|---------|
| 0 | `completed` | Delivery completed |
| 1 | `frozen` | Delivery frozen/paused |
| 2 | `in_transit` | Package in transit |
| 3 | `awaiting_pickup` | Awaiting customer pickup |
| 4 | `out_for_delivery` | Out for delivery today |
| 5 | `not_found` | Parcel not found |
| 6 | `failed_attempt` | Delivery attempt failed |
| 7 | `exception` | Delivery exception |
| 8 | `carrier_info_received` | Carrier info received, not yet in transit |

## Device Structure

Each parcel creates a device with:
- **Name**: Parcel description or tracking number
- **Manufacturer**: ParcelApp
- **Model**: Carrier code (e.g., amzlde, dp, gls)
- **Tracking Status Sensor** with attributes:
  - tracking_number, carrier, description
  - status_code, date_expected, date_expected_end
  - latest_event (with location), extra_information
  - timestamp information

## Example Automations

### Notification on Status Change

```yaml
automation:
  - alias: "Parcel Status Changed"
    trigger:
      platform: state
      entity_id: "sensor.parcelapp_*"
    condition:
      - condition: not
        conditions:
          - condition: state
            entity_id: "sensor.parcelapp_*"
            state: "completed"
    action:
      - service: "notify.mobile_app"
        data:
          title: "Parcel Update"
          message: "{{ trigger.entity_id | regex_replace('^sensor\\.parcelapp_', '') }}: {{ states(trigger.entity_id) }}"
```

### Remove Completed Parcels (Manual)

The integration automatically removes completed parcels older than 3 days. To manually trigger cleanup, reload the integration:

```yaml
service: homeassistant.reload_config_entry
data:
  entry_id: "parcelapp"
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| API key rejected | Verify key is correct and account is Premium |
| No deliveries showing | Check you have active deliveries; try "recent" filter |
| Integration won't load | Check Home Assistant logs (Settings > System > Logs) |
| Rate limited | Increase poll interval above 180 seconds |

## More Information

See [DEVELOPER.md](DEVELOPER.md) for technical details, API reference, and file structure.
