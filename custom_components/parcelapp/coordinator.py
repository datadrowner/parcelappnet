"""Update coordinator for ParcelApp integration."""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ParcelAppAPI
from .cache import ParcelAppCache
from .const import DEFAULT_REMOVAL_AGE_DAYS

_LOGGER = logging.getLogger(__name__)

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


class ParcelAppCoordinator(DataUpdateCoordinator):
    """Coordinator for ParcelApp deliveries."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ParcelAppAPI,
        poll_interval: int = 300,
        filter_mode: str = "active",
    ):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="ParcelApp",
            update_interval=timedelta(seconds=poll_interval),
        )
        self.api = api
        self.filter_mode = filter_mode
        self.hass = hass
        self.cache = ParcelAppCache()
        self._skip_first_request = False  # Flag to skip API call on first refresh if cache exists
        
        # Rate limit handling
        self._rate_limited: bool = False  # Whether we're currently rate limited
        self._rate_limit_until: Optional[datetime] = None  # When rate limit should expire
        self._probe_in_progress: bool = False  # Prevent multiple probe requests

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from the API, using cache as fallback."""
        try:
            # Check if we're rate limited and still within the wait period
            if self._rate_limited and self._rate_limit_until:
                now = datetime.now()
                
                # If still within rate limit window, use cache and skip API call
                if now < self._rate_limit_until:
                    time_remaining = (self._rate_limit_until - now).total_seconds()
                    _LOGGER.debug(
                        "API rate limited. Waiting %.0f seconds before retry. Using cached data.",
                        time_remaining
                    )
                    cached = self.cache.load_deliveries()
                    if cached:
                        return {"deliveries": cached, "cached": True, "rate_limited": True}
                    raise UpdateFailed("API rate limited. Waiting for recovery.")
                
                # Rate limit window has expired, attempt probe request
                if not self._probe_in_progress:
                    _LOGGER.info("Rate limit window expired. Attempting probe request to check API status...")
                    self._probe_in_progress = True
                    
                    probe_result = await self.api.get_deliveries(filter_mode=self.filter_mode)
                    
                    if probe_result.get("success"):
                        # API is back, reset rate limit flags
                        _LOGGER.info("✓ API is back online! Resuming normal operation.")
                        self._rate_limited = False
                        self._rate_limit_until = None
                        self._probe_in_progress = False
                        # Continue with normal request below
                    else:
                        error_msg = probe_result.get("error_message", "Unknown error")
                        if "rate limit" in error_msg.lower() or "429" in error_msg:
                            # Still rate limited, extend wait period
                            _LOGGER.warning("API still rate limited. Extending wait period.")
                            self._rate_limit_until = datetime.now() + timedelta(hours=1)
                            self._probe_in_progress = False
                            
                            cached = self.cache.load_deliveries()
                            if cached:
                                return {"deliveries": cached, "cached": True, "rate_limited": True}
                            raise UpdateFailed("API still rate limited. Waiting for recovery.")
                        else:
                            # Different error, reset rate limit state
                            _LOGGER.warning("Probe request failed with different error: %s", error_msg)
                            self._rate_limited = False
                            self._rate_limit_until = None
                            self._probe_in_progress = False
                            raise UpdateFailed(f"API error: {error_msg}")
                    
                    self._probe_in_progress = False
            
            # On first setup/reload, use cache if available to minimize API calls
            if self._skip_first_request:
                cached = self.cache.load_deliveries()
                if cached:
                    _LOGGER.info("Using cached deliveries for initial setup.")
                    return {"deliveries": cached, "cached": True}
                self._skip_first_request = False
            
            result = await self.api.get_deliveries(filter_mode=self.filter_mode)

            if not result.get("success"):
                error_msg = result.get("error_message", "Unknown error")
                
                # Handle rate limiting with retry_after
                if "rate limit" in error_msg.lower() or "429" in error_msg:
                    _LOGGER.error(
                        "ParcelApp API rate limited (HTTP 429). "
                        "No more requests will be made for 1 hour. Using cached data."
                    )
                    self._rate_limited = True
                    self._rate_limit_until = datetime.now() + timedelta(hours=1)
                    
                    # Return cached data instead of raising
                    cached = self.cache.load_deliveries()
                    if cached:
                        return {"deliveries": cached, "cached": True, "rate_limited": True}
                    
                    raise UpdateFailed(error_msg, retry_after=3600)
                
                _LOGGER.warning("ParcelApp API error: %s", error_msg)
                raise UpdateFailed(f"API error: {error_msg}")

            deliveries = result.get("deliveries", [])
            
            # Reset rate limit state on successful API call
            if self._rate_limited:
                _LOGGER.info("✓ API recovered. Resuming normal operation.")
                self._rate_limited = False
                self._rate_limit_until = None

            # Process deliveries and filter out old completed ones
            processed_deliveries = []
            for delivery in deliveries:
                delivery_data = {
                    "tracking_number": delivery.get("tracking_number"),
                    "carrier_code": delivery.get("carrier_code"),
                    "description": delivery.get("description"),
                    "status_code": delivery.get("status_code"),
                    "status_name": DELIVERY_STATUS_CODES.get(
                        delivery.get("status_code"), "unknown"
                    ),
                    "date_expected": delivery.get("date_expected"),
                    "date_expected_end": delivery.get("date_expected_end"),
                    "events": delivery.get("events", []),
                    "extra_information": delivery.get("extra_information"),
                }

                # Add timestamp fields if available
                if "timestamp_expected" in delivery:
                    delivery_data["timestamp_expected"] = delivery[
                        "timestamp_expected"
                    ]
                if "timestamp_expected_end" in delivery:
                    delivery_data["timestamp_expected_end"] = delivery[
                        "timestamp_expected_end"
                    ]

                # Check if delivery should be removed (completed and older than 3 days)
                if self._should_remove_delivery(delivery_data):
                    _LOGGER.debug(
                        f"Marking delivery {delivery_data['tracking_number']} for removal (completed 3+ days ago)"
                    )
                    delivery_data["should_remove"] = True
                else:
                    delivery_data["should_remove"] = False

                processed_deliveries.append(delivery_data)

            return {"deliveries": processed_deliveries}

        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.exception("Unexpected error updating deliveries: %s", err)
            raise UpdateFailed(f"Error updating deliveries: {err}") from err

    def _process_deliveries(self, deliveries: list) -> list:
        """Process raw deliveries and filter old completed ones."""
        processed_deliveries = []
        for delivery in deliveries:
            delivery_data = {
                "tracking_number": delivery.get("tracking_number"),
                "carrier_code": delivery.get("carrier_code"),
                "description": delivery.get("description"),
                "status_code": delivery.get("status_code"),
                "status_name": DELIVERY_STATUS_CODES.get(
                    delivery.get("status_code"), "unknown"
                ),
                "date_expected": delivery.get("date_expected"),
                "date_expected_end": delivery.get("date_expected_end"),
                "events": delivery.get("events", []),
                "extra_information": delivery.get("extra_information"),
            }

            # Add timestamp fields if available
            if "timestamp_expected" in delivery:
                delivery_data["timestamp_expected"] = delivery["timestamp_expected"]
            if "timestamp_expected_end" in delivery:
                delivery_data["timestamp_expected_end"] = delivery["timestamp_expected_end"]

            # Check if delivery should be removed (completed and older than 3 days)
            if self._should_remove_delivery(delivery_data):
                _LOGGER.debug(
                    f"Marking delivery {delivery_data['tracking_number']} for removal (completed 3+ days ago)"
                )
                delivery_data["should_remove"] = True
            else:
                delivery_data["should_remove"] = False

            processed_deliveries.append(delivery_data)
        
        return processed_deliveries

    def _should_remove_delivery(self, delivery: Dict[str, Any]) -> bool:
        """Check if a delivery should be removed (completed 3+ days ago)."""
        # Only remove if status is completed (0)
        if delivery.get("status_code") != 0:
            return False

        # Try to get the expected date
        date_str = delivery.get("date_expected")
        if not date_str:
            return False

        try:
            # Parse the date string (format: "2025-12-06 00:00:00")
            delivery_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            days_ago = (now - delivery_date).days

            # Remove if delivered 3 or more days ago
            return days_ago >= DEFAULT_REMOVAL_AGE_DAYS
        except (ValueError, TypeError) as err:
            _LOGGER.warning(f"Could not parse delivery date: {date_str}")
            return False
