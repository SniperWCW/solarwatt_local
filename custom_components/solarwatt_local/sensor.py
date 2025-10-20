from __future__ import annotations

import logging
import asyncio
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from .api import SolarwattAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = 30  # Sekunden


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Solarwatt Local sensors dynamically from config entry."""
    host = entry.data["host"]
    password = entry.data["password"]

    api = SolarwattAPI(host, password)

    async def async_update_data():
        """Fetch all items from Solarwatt REST API."""
        try:
            items = await api.get_items()
            if not items:
                raise Exception("Keine Daten vom Gateway erhalten")
            return items
        except Exception as err:
            _LOGGER.error("Fehler beim Abrufen der Items: %s", err)
            return {}

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="solarwatt_dynamic_sensors",
        update_method=async_update_data,
        update_interval=timedelta(seconds=SCAN_INTERVAL),
    )

    # erste Aktualisierung
    await coordinator.async_config_entry_first_refresh()

    # dynamische Sensoren erstellen
    sensors = [
        SolarwattGenericSensor(coordinator, item_id, data)
        for item_id, data in coordinator.data.items()
    ]

    async_add_entities(sensors)

    # Session sauber schließen bei HA Stop
    async def async_close_session(event):
        await api.close()

    hass.bus.async_listen_once("homeassistant_stop", async_close_session)


class SolarwattGenericSensor(CoordinatorEntity, SensorEntity):
    """Dynamischer Sensor für ein REST-Item."""

    def __init__(self, coordinator, item_id, initial_data):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.item_id = item_id
        self._attr_unique_id = f"solarwatt_{item_id}"
        self._attr_name = f"Solarwatt {item_id.replace('_', ' ')}"

    @property
    def native_value(self):
        value = self.coordinator.data.get(self.item_id)
        if not value:
            return None
        if isinstance(value, dict):
            state = value.get("state")
        else:
            state = value

        # Versuche, Zahlenwerte zu extrahieren
        try:
            if isinstance(state, str) and any(c in state for c in ["W", "%", "kWh"]):
                num = "".join(ch for ch in state if (ch.isdigit() or ch == "." or ch == "-"))
                return float(num) if num else state
            return float(state)
        except Exception:
            return state or "unbekannt"
