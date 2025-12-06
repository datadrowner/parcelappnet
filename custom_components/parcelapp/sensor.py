"""Sensor platform for ParcelApp integration."""
import logging
from typing import Optional

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN
from .coordinator import DELIVERY_STATUS_CODES

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up ParcelApp sensors from discovery info."""
    if discovery_info is None:
        return

    coordinator = discovery_info["coordinator"]
    async_add_entities(
        [
            ParcelAppSensor(coordinator, delivery["tracking_number"])
            for delivery in coordinator.data.get("deliveries", [])
        ]
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: "ConfigEntry",
    async_add_entities: AddEntitiesCallback,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up ParcelApp sensors from config entry."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN]["coordinator"]

    sensors = []
    if coordinator.data:
        for delivery in coordinator.data.get("deliveries", []):
            sensors.append(ParcelAppSensor(coordinator, delivery["tracking_number"]))

    async_add_entities(sensors)


class ParcelAppSensor(CoordinatorEntity, SensorEntity):
    """Sensor for a ParcelApp delivery."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: DataUpdateCoordinator, tracking_number: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.tracking_number = tracking_number
        self._attr_unique_id = f"parcelapp_{tracking_number}"
        self._attr_name = "Tracking Status"

    @property
    def device_info(self):
        """Return device info for this delivery."""
        delivery = self._get_delivery()
        if not delivery:
            return None

        return {
            "identifiers": {("parcelapp", self.tracking_number)},
            "name": delivery.get("description", self.tracking_number),
            "manufacturer": "ParcelApp",
            "model": delivery.get("carrier_code", "Unknown"),
            "sw_version": "1.0.0",
        }

    @property
    def state(self) -> Optional[str]:
        """Return the state of the sensor."""
        delivery = self._get_delivery()
        if not delivery:
            return STATE_UNKNOWN

        status_code = delivery.get("status_code")
        return DELIVERY_STATUS_CODES.get(status_code, STATE_UNKNOWN)

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        delivery = self._get_delivery()
        if not delivery:
            return {}

        # Get the most recent event
        events = delivery.get("events", [])
        latest_event = None
        if events:
            latest_event = {
                "event": events[0].get("event"),
                "date": events[0].get("date"),
                "location": events[0].get("location"),
                "additional": events[0].get("additional"),
            }

        attributes = {
            "tracking_number": delivery.get("tracking_number"),
            "carrier": delivery.get("carrier_code"),
            "description": delivery.get("description"),
            "status_code": delivery.get("status_code"),
            "date_expected": delivery.get("date_expected"),
            "latest_event": latest_event,
        }

        # Add optional fields if present
        if delivery.get("date_expected_end"):
            attributes["date_expected_end"] = delivery.get("date_expected_end")
        if delivery.get("extra_information"):
            attributes["extra_information"] = delivery.get("extra_information")
        if delivery.get("timestamp_expected"):
            attributes["timestamp_expected"] = delivery.get("timestamp_expected")
        if delivery.get("timestamp_expected_end"):
            attributes["timestamp_expected_end"] = delivery.get(
                "timestamp_expected_end"
            )

        return attributes

    def _get_delivery(self):
        """Get the delivery data for this sensor."""
        if not self.coordinator.data:
            return None

        deliveries = self.coordinator.data.get("deliveries", [])
        for delivery in deliveries:
            if delivery.get("tracking_number") == self.tracking_number:
                return delivery

        return None
