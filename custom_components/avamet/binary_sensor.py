"""Recent rain for automations, without the misleading moisture device class."""

from homeassistant.components.binary_sensor import BinarySensorEntity

from .entity import AvametEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    if entry.runtime_data.data.observation.supports_rain:
        async_add_entities([AvametRaining(entry.runtime_data)])


class AvametRaining(AvametEntity, BinarySensorEntity):
    _attr_translation_key = "raining"
    _attr_icon = "mdi:weather-rainy"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "raining")

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.is_raining is not None

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.is_raining

    @property
    def extra_state_attributes(self):
        return {"rain_window_minutes": 10}
