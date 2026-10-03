"""Observation-only weather: unknown sky is not automatically sunny."""

from homeassistant.components.weather import WeatherEntity
from homeassistant.const import UnitOfLength, UnitOfPressure, UnitOfSpeed, UnitOfTemperature

from .entity import AvametEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    if "temperature_c" in entry.runtime_data.data.observation.values:
        async_add_entities([AvametWeather(entry.runtime_data)])


class AvametWeather(AvametEntity, WeatherEntity):
    _attr_name = None
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_native_precipitation_unit = UnitOfLength.MILLIMETERS
    _attr_attribution = "Observaciones públicas de AVAMET"
    _attr_supported_features = 0

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "weather")

    @property
    def condition(self) -> str | None:
        return self.coordinator.data.condition(self.coordinator.windy_threshold)

    @property
    def native_temperature(self):
        return self.coordinator.data.observation.values.get("temperature_c")

    @property
    def humidity(self):
        return self.coordinator.data.observation.values.get("humidity_percent")

    @property
    def native_pressure(self):
        return self.coordinator.data.observation.values.get("pressure_hpa")

    @property
    def native_wind_speed(self):
        return self.coordinator.data.observation.values.get("wind_speed_kmh")

    @property
    def wind_bearing(self):
        return self.coordinator.data.observation.values.get("wind_bearing")

    @property
    def available(self) -> bool:
        return super().available and self.native_temperature is not None

    @property
    def extra_state_attributes(self):
        snapshot = self.coordinator.data
        observation = snapshot.observation
        return {
            "station_id": observation.station_id,
            "observed_at": observation.observed_at.isoformat(),
            "from_cache": snapshot.from_cache,
            "rain_window_minutes": 10,
            "windy_threshold_kmh": self.coordinator.windy_threshold,
            "source_url": observation.source_url,
            "rain_today_mm": observation.values.get("rain_today_mm"),
            "rain_last_10_minutes_mm": None
            if snapshot.from_cache
            else observation.rain_last_10_minutes_mm,
            "daily_max_wind_gust_kmh": observation.values.get("daily_max_wind_gust_kmh"),
        }
