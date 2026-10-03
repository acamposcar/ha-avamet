"""Station identity and availability shared by all platforms."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AvametCoordinator


class AvametEntity(CoordinatorEntity[AvametCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: AvametCoordinator, key: str) -> None:
        super().__init__(coordinator)
        observation = coordinator.data.observation
        self._attr_unique_id = f"{observation.station_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, observation.station_id)},
            name=f"AVAMET {observation.station_name}",
            manufacturer="AVAMET",
            model=observation.station_id,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=observation.source_url,
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.observation_available
