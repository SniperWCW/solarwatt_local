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
    """Set up the Solarwatt integration."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Solarwatt from a config entry."""
    host = entry.data.get("host")
    password = entry.data.get("password")
    scan_seconds = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    scan_interval = timedelta(seconds=scan_seconds)

    api = SolarwattAPI(host, password)

    async def async_update_data():
        try:
            items = await api.get_items()
            return items
        except Exception as err:
            _LOGGER.error("Konnte keine Daten von Solarwatt abrufen: %s", err)
            raise UpdateFailed(err)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="solarwatt",
        update_method=async_update_data,
        update_interval=scan_interval,
    )

    # Erste Datenaktualisierung
    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed:
        _LOGGER.error("Initiales Abrufen der Solarwatt-Daten fehlgeschlagen")
        return False

    # Speichern für andere Plattformen
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "platforms_loaded": [],
    }

    # Plattformen laden
    for platform in PLATFORMS:
        try:
            await hass.config_entries.async_forward_entry_setups(entry, [platform])
            hass.data[DOMAIN][entry.entry_id]["platforms_loaded"].append(platform)
        except Exception as e:
            _LOGGER.error("Fehler beim Laden der Plattform %s: %s", platform, e)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    if not data:
        return True

    platforms_loaded = data.get("platforms_loaded", [])
    unload_ok = True
    for platform in platforms_loaded:
        try:
            result = await hass.config_entries.async_unload_platforms(entry, [platform])
            unload_ok = unload_ok and result
        except Exception as e:
            _LOGGER.error("Fehler beim Entladen der Plattform %s: %s", platform, e)
            unload_ok = False

    api = data.get("api")
    if api:
        await api.close()

    hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
