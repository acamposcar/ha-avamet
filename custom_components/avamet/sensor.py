"""Only publish measurements that the configured station actually supports."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)

from .entity import AvametEntity


@dataclass(frozen=True, kw_only=True)
class AvametSensorDescription(SensorEntityDescription):
    source: str = "values"


MEASUREMENTS = (
    AvametSensorDescription(
        key="temperature_c",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AvametSensorDescription(
        key="temperature_min_c",
        translation_key="temperature_min",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AvametSensorDescription(
        key="temperature_max_c",
        translation_key="temperature_max",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AvametSensorDescription(
        key="humidity_percent",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AvametSensorDescription(
        key="pressure_hpa",
        translation_key="pressure",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        native_unit_of_measurement=UnitOfPressure.HPA,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AvametSensorDescription(
        key="wind_speed_kmh",
        translation_key="wind_speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AvametSensorDescription(
        key="daily_max_wind_gust_kmh",
        translation_key="daily_max_wind_gust",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AvametSensorDescription(
        key="wind_direction", translation_key="wind_direction", icon="mdi:compass-outline"
    ),
    AvametSensorDescription(
        key="rain_today_mm",
        translation_key="rain_today",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    AvametSensorDescription(
        key="rain_month_mm",
        translation_key="rain_month",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    AvametSensorDescription(
        key="rain_year_mm",
        translation_key="rain_year",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
)
RAIN_MEASUREMENTS = tuple(
    AvametSensorDescription(
        key=f"rain_last_{minutes}_minutes_mm",
        translation_key=f"rain_last_{minutes}",
        source="recent_rain",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
    )
    for minutes in (5, 10)
)
DIAGNOSTICS = (
    AvametSensorDescription(
        key="observed_at",
        translation_key="observed_at",
        source="observation",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator = entry.runtime_data
    observation = coordinator.data.observation
    descriptions = [desc for desc in MEASUREMENTS if desc.key in observation.values]
    descriptions.extend(DIAGNOSTICS)
    entities = [AvametSensor(coordinator, desc) for desc in descriptions]
    if observation.supports_rain:
        entities.extend(AvametSensor(coordinator, desc) for desc in RAIN_MEASUREMENTS)
        entities.append(AvametRainStatus(coordinator))
    async_add_entities(entities)


class AvametSensor(AvametEntity, SensorEntity):
    entity_description: AvametSensorDescription

    def __init__(self, coordinator, description: AvametSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        observation = self.coordinator.data.observation
        if self.entity_description.source == "observation":
            return getattr(observation, self.entity_description.key)
        if self.entity_description.source == "recent_rain":
            if self.coordinator.data.from_cache:
                return None
            return getattr(observation, self.entity_description.key)
        return observation.values.get(self.entity_description.key)

    @property
    def available(self) -> bool:
        return super().available and self.native_value is not None

    @property
    def extra_state_attributes(self):
        if self.entity_description.key != "observed_at":
            return None
        snapshot = self.coordinator.data
        return {
            "station_id": snapshot.observation.station_id,
            "fetched_at": snapshot.observation.fetched_at.isoformat(),
            "attempted_at": snapshot.attempted_at.isoformat(),
            "from_cache": snapshot.from_cache,
            "last_error": snapshot.last_error,
            "rain_error": snapshot.observation.rain_error,
            "source_url": snapshot.observation.source_url,
        }


class AvametRainStatus(AvametEntity, SensorEntity):
    _attr_translation_key = "rain_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["raining", "dry"]
    _attr_icon = "mdi:weather-rainy"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "rain_status")

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.is_raining is not None

    @property
    def native_value(self) -> str | None:
        raining = self.coordinator.data.is_raining
        return None if raining is None else "raining" if raining else "dry"

    @property
    def extra_state_attributes(self):
        return {"rain_window_minutes": 10}
