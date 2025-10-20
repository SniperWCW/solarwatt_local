from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SolarwattAPI
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data.get("host")
    password = entry.data.get("password")
    scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)

    session = None
    api = SolarwattAPI(host, password, session=session)

    async def async_update_data():
        try:
            items = await api.get_items()
            return items
        except Exception as err:
            raise UpdateFailed(err)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="solarwatt",
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )

    # erste Aktualisierung
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    api = hass.data[DOMAIN][entry.entry_id].get("api")
    if api:
        await api.close()
    hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
