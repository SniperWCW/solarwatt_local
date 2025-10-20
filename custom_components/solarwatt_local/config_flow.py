import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .api import SolarwattAPI

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Required("password"): str,
        vol.Optional("scan_interval", default=DEFAULT_SCAN_INTERVAL): int,
    }
)

class SolarwattConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            host = user_input["host"]
            password = user_input["password"]
            api = SolarwattAPI(host, password)

            try:
                await api.get_items()
            except Exception as e:
                _LOGGER.error("Fehler beim Verbinden zu Solarwatt: %s", e)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Solarwatt {host}", data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
