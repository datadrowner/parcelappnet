"""ParcelApp integration for Home Assistant."""
import asyncio
import logging
from typing import Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceRegistry, async_get as async_get_device_registry

from .api import ParcelAppAPI
from .const import DOMAIN, PLATFORMS, DEFAULT_POLL_INTERVAL, MIN_POLL_INTERVAL, DEFAULT_FILTER_MODE
from .coordinator import ParcelAppCoordinator

_LOGGER = logging.getLogger(__name__)



async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ParcelApp from a config entry."""
    try:
        hass.data.setdefault(DOMAIN, {})

        api_key = entry.data.get("api_key")
        if not api_key:
            _LOGGER.error("No API key found in configuration")
            return False

        poll_interval = entry.options.get("poll_interval", DEFAULT_POLL_INTERVAL)
        # Enforce minimum poll interval to respect API rate limits (20 req/hour max)
        if poll_interval < MIN_POLL_INTERVAL:
            _LOGGER.warning(
                "Poll interval %d is below minimum %d seconds. Using minimum to respect API limits.",
                poll_interval,
                MIN_POLL_INTERVAL,
            )
            poll_interval = MIN_POLL_INTERVAL
        filter_mode = entry.options.get("filter_mode", DEFAULT_FILTER_MODE)

        api = ParcelAppAPI(api_key)
        coordinator = ParcelAppCoordinator(
            hass, api, poll_interval=poll_interval, filter_mode=filter_mode
        )

        # On setup, try to use cache first if available to minimize API calls
        if coordinator.cache:
            try:
                cached_deliveries = coordinator.cache.load_deliveries()
                if cached_deliveries:
                    _LOGGER.info("Using cached deliveries on setup to minimize API calls.")
                    coordinator._skip_first_request = True
            except Exception as cache_err:
                _LOGGER.warning("Failed to load cache on setup: %s", cache_err)

        # Fetch initial data (will use cache if flag is set)
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

    except Exception as err:
        _LOGGER.exception("Error setting up ParcelApp integration: %s", err)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

        if unload_ok:
            entry_data = hass.data[DOMAIN].get(entry.entry_id)
            if entry_data:
                api = entry_data.get("api")
                if api:
                    try:
                        await api.close()
                    except Exception as err:
                        _LOGGER.debug("Error closing API session: %s", err)
                hass.data[DOMAIN].pop(entry.entry_id)

        return unload_ok

    except Exception as err:
        _LOGGER.exception("Error unloading ParcelApp integration: %s", err)
        return False


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_cleanup_old_deliveries(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Clean up old delivered parcels and their devices."""
    while True:
        try:
            # Check if entry still exists
            if config_entry.entry_id not in hass.data.get(DOMAIN, {}):
                _LOGGER.debug("Config entry removed, stopping cleanup task")
                break

            coordinator: ParcelAppCoordinator = hass.data[DOMAIN][config_entry.entry_id][
                "coordinator"
            ]
            device_registry: DeviceRegistry = async_get_device_registry(hass)

            # Check coordinator data for deliveries marked for removal
            if coordinator.data:
                deliveries = coordinator.data.get("deliveries", [])

                for delivery in deliveries:
                    try:
                        if delivery.get("should_remove"):
                            tracking_number = delivery.get("tracking_number")
                            _LOGGER.info(
                                "Removing old delivered parcel: %s", tracking_number
                            )

                            # Find and remove the device
                            device = device_registry.async_get_device(
                                identifiers={(
"parcelapp", tracking_number)}
                            )
                            if device:
                                device_registry.async_remove_device(device.id)
                                _LOGGER.debug(
                                    "Removed device for tracking number: %s", tracking_number
                                )
                    except Exception as err:
                        _LOGGER.error(
                            "Error removing device %s: %s",
                            delivery.get("tracking_number", "unknown"),
                            err,
                        )

            # Wait for the next coordinator update before checking again
            await coordinator.async_refresh()

        except asyncio.CancelledError:
            _LOGGER.debug("Cleanup task cancelled")
            break
        except Exception as err:
            _LOGGER.error("Error in cleanup task: %s", err, exc_info=True)
            # Continue running even if there's an error
            await asyncio.sleep(60)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up ParcelApp integration from YAML configuration."""
    # This integration only supports config flow
    return True
