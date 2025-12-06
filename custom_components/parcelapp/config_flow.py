"""Config flow for ParcelApp integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api import ParcelAppAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Optional("poll_interval", default=300): int,
        vol.Optional("filter_mode", default="active"): vol.In(["active", "recent"]),
    }
)


async def validate_api_key(hass: HomeAssistant, api_key: str) -> bool:
    """Validate the API key by making a test request."""
    api = ParcelAppAPI(api_key)
    try:
        result = await api.get_deliveries()
        await api.close()
        return result.get("success", False)
    except Exception as err:
        _LOGGER.error(f"Error validating API key: {err}")
        await api.close()
        return False


class ParcelAppConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for ParcelApp."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is not None:
            # Check if already configured
            await self.async_set_unique_id("parcelapp")
            self._abort_if_unique_id_configured()

            api_key = user_input.get(CONF_API_KEY)

            # Validate API key
            if not await validate_api_key(self.hass, api_key):
                errors["base"] = "invalid_auth"
            else:
                return self.async_create_entry(
                    title="ParcelApp",
                    data={
                        CONF_API_KEY: api_key,
                    },
                    options={
                        "poll_interval": user_input.get("poll_interval", 300),
                        "filter_mode": user_input.get("filter_mode", "active"),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=CONFIG_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this config entry."""
        return ParcelAppOptionsFlow(config_entry)


class ParcelAppOptionsFlow(config_entries.OptionsFlow):
    """Options flow for ParcelApp."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema(
            {
                vol.Optional(
                    "poll_interval",
                    default=self.config_entry.options.get("poll_interval", 300),
                ): int,
                vol.Optional(
                    "filter_mode",
                    default=self.config_entry.options.get("filter_mode", "active"),
                ): vol.In(["active", "recent"]),
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
