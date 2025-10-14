"""HTTP Agent integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_SENSOR_TYPE, CONF_SENSORS, DOMAIN
from .coordinator import HTTPAgentCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.DEVICE_TRACKER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HTTP Agent from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Merge options into data for coordinator
    data = dict(entry.data)
    if entry.options:
        data.update(entry.options)

    coordinator = HTTPAgentCoordinator(hass, data)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Determine which platforms are needed based on sensor types
    data = dict(entry.data)
    if entry.options:
        data.update(entry.options)

    needed_platforms = set()
    for sensor_config in data.get(CONF_SENSORS, []):
        sensor_type = sensor_config.get(CONF_SENSOR_TYPE, "sensor")
        if sensor_type == "sensor":
            needed_platforms.add(Platform.SENSOR)
        elif sensor_type == "binary_sensor":
            needed_platforms.add(Platform.BINARY_SENSOR)
        elif sensor_type == "number":
            needed_platforms.add(Platform.NUMBER)
        elif sensor_type == "device_tracker":
            needed_platforms.add(Platform.DEVICE_TRACKER)

    # Store coordinator and setup platforms info
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "platforms": list(needed_platforms)
    }

    # Set up only needed platforms
    if needed_platforms:
        await hass.config_entries.async_forward_entry_setups(
            entry, list(needed_platforms)
        )

    # Add options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]
    setup_platforms = entry_data["platforms"]

    # Clean up the coordinator's session
    await coordinator.async_close()

    # Only unload platforms that were actually set up for this entry
    if setup_platforms:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, setup_platforms)
    else:
        unload_ok = True

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
