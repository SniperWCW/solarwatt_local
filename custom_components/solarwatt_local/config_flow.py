from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .api import SolarwattAPI

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Required("password"): str,
        vol.Optional("scan_interval", default=DEFAULT_SCAN_INTERVAL): int,
    }
)


class SolarwattConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solarwatt Local integration."""

    VERSION = 1

    async def async_step_user(self, user_input: ConfigType | None = None):
        errors = {}

        if user_input is not None:
            host = user_input["host"]
            password = user_input["password"]

            api = SolarwattAPI(host, password)

            try:
                # Test connection
                await api.get_items()
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="Solarwatt Local", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
