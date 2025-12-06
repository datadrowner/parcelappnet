"""Constants for ParcelApp integration."""

DOMAIN = "parcelapp"
PLATFORMS = ["sensor"]

# Configuration defaults
DEFAULT_POLL_INTERVAL = 360  # 6 minutes = 10 requests per hour (API limit is 20/hour, stay safe)
MIN_POLL_INTERVAL = 360  # Minimum 6 minutes to stay within API limits
DEFAULT_FILTER_MODE = "active"
DEFAULT_REMOVAL_AGE_DAYS = 3

# Status code mappings
DELIVERY_STATUS_CODES = {
    0: "completed",
    1: "frozen",
    2: "in_transit",
    3: "awaiting_pickup",
    4: "out_for_delivery",
    5: "not_found",
    6: "failed_attempt",
    7: "exception",
    8: "carrier_info_received",
}
