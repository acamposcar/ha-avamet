"""AVAMET integration; the parser can also be used without Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

PLATFORMS = ("sensor", "binary_sensor", "weather")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Create one coordinator per station and set up supported entities."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .api import AvametClient
    from .coordinator import AvametCoordinator

    coordinator = AvametCoordinator(
        hass, entry, AvametClient(async_get_clientsession(hass), entry.data["station_id"])
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.cancel_expiry)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the station, listeners and timers."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply options using Home Assistant's normal entry lifecycle."""
    await hass.config_entries.async_reload(entry.entry_id)
