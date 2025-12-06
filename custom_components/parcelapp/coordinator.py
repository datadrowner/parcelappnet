"""Update coordinator for ParcelApp integration."""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ParcelAppAPI
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

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from the API."""
        try:
            result = await self.api.get_deliveries(filter_mode=self.filter_mode)

            if not result.get("success"):
                raise UpdateFailed(f"API error: {result.get('error_message')}")

            deliveries = result.get("deliveries", [])

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

        except Exception as err:
            raise UpdateFailed(f"Error updating deliveries: {err}")

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
        except ValueError:
            _LOGGER.warning(f"Could not parse delivery date: {date_str}")
            return False
