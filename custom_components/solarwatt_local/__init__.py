from __future__ import annotations

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
    """Set up the integration (no config flow)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Solarwatt Local from a config entry."""
    host = entry.data.get("host")
    password = entry.data.get("password")
    scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)

    api = SolarwattAPI(host, password)

    async def async_update_data():
        try:
            return await api.get_items()
        except Exception as err:
            _LOGGER.error("Fehler beim Abrufen der Items: %s", err)
            raise UpdateFailed(err)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"solarwatt_{host}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )

    # Erste Aktualisierung, um sicherzustellen, dass die Verbindung klappt
    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as err:
        _LOGGER.error("Solarwatt Verbindung fehlgeschlagen beim ersten Refresh: %s", err)
        await api.close()
        return False

    # Daten in hass.data speichern
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    # Plattformen laden
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    api = hass.data[DOMAIN][entry.entry_id].get("api")
    if api:
        await api.close()
    hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
