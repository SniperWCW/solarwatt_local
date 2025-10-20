from __future__ import annotations


import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN


STEP_USER_DATA_SCHEMA = vol.Schema({
vol.Required("host"): str,
vol.Required("password"): str,
vol.Optional("scan_interval", default=15): int,
})




class SolarwattConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
VERSION = 1


async def async_step_user(self, user_input=None):
if user_input is None:
return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA)


# validate by trying to login and fetch items
host = user_input["host"]
password = user_input["password"]
scan_interval = user_input.get("scan_interval", 15)


from .api import SolarwattAPI
api = SolarwattAPI(host, password)
try:
await api.login()
items = await api.get_items()
except Exception as err:
return self.async_show_form(
step_id="user",
data_schema=STEP_USER_DATA_SCHEMA,
errors={"base": "auth"},
)
await api.close()


return self.async_create_entry(title=f"Solarwatt {host}", data={"host": host, "password": password}, options={"scan_interval": scan_interval})
