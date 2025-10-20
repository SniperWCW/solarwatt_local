import logging
import asyncio
import aiohttp
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity

_LOGGER = logging.getLogger(__name__)
DOMAIN = "solarwatt_local"

SCAN_INTERVAL = timedelta(seconds=30)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Solarwatt Local sensors dynamically."""
    host = entry.data.get("host")
    username = entry.data.get("username") or entry.data.get("user") or "installer"
    password = entry.data.get("password")

    session = aiohttp.ClientSession()

    async def login():
        login_url = f"http://{host}/auth/login"
        data = {"username": username, "password": password, "url": "/"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            async with session.post(login_url, data=data, headers=headers, timeout=10, allow_redirects=True) as resp:
                text = await resp.text()
                cookies = session.cookie_jar.filter_cookies(f"http://{host}")
                if not cookies:
                    _LOGGER.error("Keine Cookies nach Login erhalten, HTML-Antwort: %s", text[:200])
                    return False
                return True
        except Exception as e:
            _LOGGER.error("Login Exception: %s", e)
            return False

    async def fetch_items():
        if not await login():
            return {}
        url = f"http://{host}/rest/items"
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    _LOGGER.error("Fehler beim Abrufen der Items: HTTP %s", resp.status)
                    return {}
                try:
                    return await resp.json()
                except Exception:
                    text = await resp.text()
                    _LOGGER.warning("Antwort ist kein JSON, Text: %s", text[:200])
                    return {}
        except Exception as e:
            _LOGGER.error("Verbindung zu Solarwatt fehlgeschlagen: %s", e)
            return {}

    # Initialen Abruf
    items = await fetch_items()
    if not items:
        _LOGGER.error("Keine Items empfangen – keine Sensoren erstellt.")
        await session.close()
        return

    # DataUpdateCoordinator
    async def async_update_data():
        data = {}
        for item in items:
            name = item.get("name") or item.get("label")
            if not name:
                continue
            item_url = f"http://{host}/rest/items/{name}"
            try:
                async with session.get(item_url, timeout=10) as resp:
                    if resp.status != 200:
                        continue
                    try:
                        data[name] = await resp.json()
                    except Exception:
                        text = await resp.text()
                        data[name] = {"state": text.strip()}
            except Exception as e:
                _LOGGER.warning("Fehler bei %s: %s", item_url, e)
        return data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Solarwatt Local Dynamic Sensors",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()

    # Sensoren dynamisch anlegen
    sensors = [SolarwattGenericSensor(coordinator, item.get("name") or item.get("label"), item)
               for item in coordinator.data.values() if item]
    if sensors:
        async_add_entities(sensors)
        _LOGGER.info("Solarwatt: %s Sensoren initialisiert.", len(sensors))
    else:
        _LOGGER.warning("Keine Sensoren erstellt – prüfe REST-Antwort.")

    async def async_close_session(event):
        await session.close()

    hass.bus.async_listen_once("homeassistant_stop", async_close_session)


class SolarwattGenericSensor(CoordinatorEntity, SensorEntity):
    """Dynamisch erzeugter Sensor für jedes REST-Item."""

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
        # Versuche, Zahlenwerte zu interpretieren
        try:
            if isinstance(state, str) and any(c in state for c in ["W", "%", "kWh"]):
                num = ''.join(ch for ch in state if (ch.isdigit() or ch == '.' or ch == '-'))
                return float(num) if num else state
            return float(state)
        except Exception:
            return state or "unbekannt"
