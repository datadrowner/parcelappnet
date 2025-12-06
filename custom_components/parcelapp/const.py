"""Constants for ParcelApp integration."""

DOMAIN = "parcelapp"
PLATFORMS = ["sensor"]

# Configuration defaults
DEFAULT_POLL_INTERVAL = 300  # 5 minutes
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
