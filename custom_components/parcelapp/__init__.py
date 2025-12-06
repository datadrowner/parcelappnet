"""ParcelApp integration for Home Assistant."""
import asyncio
import logging
from typing import Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceRegistry, async_get as async_get_device_registry

from .api import ParcelAppAPI
from .const import DOMAIN, PLATFORMS
from .coordinator import ParcelAppCoordinator

_LOGGER = logging.getLogger(__name__)

# Default configuration
DEFAULT_POLL_INTERVAL = 300  # 5 minutes
DEFAULT_FILTER_MODE = "active"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ParcelApp from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api_key = entry.data.get("api_key")
    poll_interval = entry.options.get("poll_interval", DEFAULT_POLL_INTERVAL)
    filter_mode = entry.options.get("filter_mode", DEFAULT_FILTER_MODE)

    api = ParcelAppAPI(api_key)
    coordinator = ParcelAppCoordinator(
        hass, api, poll_interval=poll_interval, filter_mode=filter_mode
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Set up listeners for options updates
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    # Schedule device cleanup task
    hass.async_create_task(async_cleanup_old_deliveries(hass, entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        api = hass.data[DOMAIN][entry.entry_id].get("api")
        if api:
            await api.close()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_cleanup_old_deliveries(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Clean up old delivered parcels and their devices."""
    coordinator: ParcelAppCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]
    device_registry: DeviceRegistry = async_get_device_registry(hass)

    while True:
        try:
            # Check coordinator data for deliveries marked for removal
            if coordinator.data:
                deliveries = coordinator.data.get("deliveries", [])

                for delivery in deliveries:
                    if delivery.get("should_remove"):
                        tracking_number = delivery.get("tracking_number")
                        _LOGGER.info(
                            f"Removing old delivered parcel: {tracking_number}"
                        )

                        # Find and remove the device
                        device = device_registry.async_get_device(
                            identifiers={("parcelapp", tracking_number)}
                        )
                        if device:
                            device_registry.async_remove_device(device.id)
                            _LOGGER.debug(
                                f"Removed device for tracking number: {tracking_number}"
                            )

            # Wait for the next coordinator update before checking again
            await coordinator.async_refresh()

        except Exception as err:
            _LOGGER.error(f"Error in cleanup task: {err}")
            # Continue running even if there's an error
            await asyncio.sleep(60)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up ParcelApp integration from YAML configuration."""
    # This integration only supports config flow
    return True
