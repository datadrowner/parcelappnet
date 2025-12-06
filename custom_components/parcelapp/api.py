"""ParcelApp API client."""
import aiohttp
import logging
from typing import Optional, Dict, Any, List

_LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://api.parcel.app/external"


class ParcelAppAPI:
    """ParcelApp API client."""

    def __init__(self, api_key: str):
        """Initialize the API client."""
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def async_get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key."""
        return {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }

    async def get_deliveries(
        self, filter_mode: str = "recent"
    ) -> Dict[str, Any]:
        """Get deliveries from ParcelApp API.

        Args:
            filter_mode: Either "active" or "recent". Default is "recent".

        Returns:
            API response dict with success status and deliveries list.
        """
        try:
            session = await self.async_get_session()
            url = f"{API_BASE_URL}/deliveries/?filter_mode={filter_mode}"

            async with session.get(url, headers=self._get_headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    _LOGGER.debug("API response: %s", data)
                    return data
                elif resp.status == 429:
                    # Rate limited
                    error_text = await resp.text()
                    _LOGGER.warning(
                        "API rate limited (429). Response: %s", error_text
                    )
                    return {
                        "success": False,
                        "error_message": "You were rate limited, please do not send more than 20 requests per hour.",
                    }
                else:
                    error_text = await resp.text()
                    _LOGGER.error(
                        "API request failed with status %s: %s", resp.status, error_text
                    )
                    return {
                        "success": False,
                        "error_message": f"HTTP {resp.status}",
                    }
        except aiohttp.ClientError as err:
            _LOGGER.error(f"API request failed: {err}")
            return {"success": False, "error_message": str(err)}
        except Exception as err:
            _LOGGER.error(f"Unexpected error: {err}")
            return {"success": False, "error_message": str(err)}

    async def add_delivery(
        self,
        tracking_number: str,
        carrier_code: str,
        description: str,
        language: Optional[str] = "en",
        send_push_confirmation: bool = False,
    ) -> Dict[str, Any]:
        """Add a new delivery to ParcelApp.

        Args:
            tracking_number: The tracking number.
            carrier_code: The carrier code.
            description: Description for the delivery.
            language: Language code (ISO 639-1).
            send_push_confirmation: Whether to send push notification.

        Returns:
            API response dict with success status.
        """
        try:
            session = await self.async_get_session()
            url = f"{API_BASE_URL}/add-delivery/"

            payload = {
                "tracking_number": tracking_number,
                "carrier_code": carrier_code,
                "description": description,
                "language": language,
                "send_push_confirmation": send_push_confirmation,
            }

            async with session.post(
                url, headers=self._get_headers(), json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    _LOGGER.debug(f"Add delivery response: {data}")
                    return data
                else:
                    _LOGGER.error(
                        f"Add delivery failed with status {resp.status}: {await resp.text()}"
                    )
                    return {
                        "success": False,
                        "error_message": f"HTTP {resp.status}",
                    }
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Add delivery request failed: {err}")
            return {"success": False, "error_message": str(err)}
        except Exception as err:
            _LOGGER.error(f"Unexpected error: {err}")
            return {"success": False, "error_message": str(err)}
