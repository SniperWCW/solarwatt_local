from __future__ import annotations


def _parse_numeric_state(state: str):
if state is None:
return None
# remove unit characters, keep digits, dot and minus
cleaned = ''.join(ch for ch in state if (ch.isdigit() or ch in ['.', '-']))
try:
return float(cleaned) if cleaned != '' else None
except Exception:
return None




class SolarwattSensor(CoordinatorEntity, SensorEntity):
def __init__(self, coordinator: DataUpdateCoordinator, item: dict):
super().__init__(coordinator)
self._item = item
self._attr_name = item.get("name")
self._attr_unique_id = item.get("name")
self._attr_native_value = None
# guess device class/unit
itype = item.get("type", "")
state = item.get("state")
if "Power" in itype or (isinstance(state, str) and "W" in state):
self._attr_device_class = DEVICE_CLASS_POWER
self._unit = POWER_WATT
elif "Battery" in itype or (isinstance(state, str) and "%" in state):
self._attr_device_class = DEVICE_CLASS_BATTERY
self._unit = "%"
else:
self._attr_device_class = None
self._unit = None


@property
def native_unit_of_measurement(self):
return self._unit


@property
def native_value(self):
state = self._item.get("state")
# try numeric parse
val = _parse_numeric_state(state)
return val


@property
def extra_state_attributes(self):
return {"raw_state": self._item.get("state"), "type": self._item.get("type"), "label": self._item.get("label")}


@property
def available(self) -> bool:
return self._item is not None


@callback
def _handle_coordinator_update(self) -> None:
# coordinator updates data (list of items). find own item and update
data = self.coordinator.data or []
for it in data:
if it.get("name") == self._item.get("name"):
self._item = it
break
self.async_write_ha_state()




async def async_setup_entry(hass: HomeAssistantType, entry, async_add_entities: AddEntitiesCallback):
api = hass.data[DOMAIN][entry.entry_id]["api"]
coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]


# create sensors for items: all Number:* and items with W or % in state
entities = []
data = coordinator.data or []
for item in data:
itype = item.get("type", "")
state = item.get("state", "")
if itype.startswith("Number") or (isinstance(state, str) and ("W" in state or "%" in state)):
entities.append(SolarwattSensor(coordinator, item))


async_add_entities(entities, True)
