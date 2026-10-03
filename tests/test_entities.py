from dataclasses import replace
from datetime import timedelta
from unittest.mock import Mock, patch

from custom_components.avamet import binary_sensor, diagnostics, sensor, weather
from custom_components.avamet.coordinator import AvametCoordinator
from custom_components.avamet.models import Snapshot
from custom_components.avamet.parser import parse_observation


def make_coordinator(hass, entry, html, now):
    coordinator = AvametCoordinator(hass, entry, Mock(station_id="c13m207e02"))
    coordinator.data = Snapshot(parse_observation(html, "c13m207e02", now=now))
    coordinator.last_update_success = True
    entry.runtime_data = coordinator
    return coordinator


async def test_all_platforms_share_single_observation(hass, entry, html, now):
    coordinator = make_coordinator(hass, entry, html, now)
    entities = []
    for platform in (sensor, binary_sensor, weather):
        await platform.async_setup_entry(hass, entry, entities.extend)
    assert len(entities) == 17
    assert len({entity.unique_id for entity in entities}) == len(entities)
    with patch("custom_components.avamet.coordinator.dt_util.utcnow", return_value=now):
        assert all(entity.available for entity in entities)
    meteorology = next(entity for entity in entities if isinstance(entity, weather.AvametWeather))
    assert meteorology.condition == "rainy"
    assert meteorology.native_temperature == 30.1
    assert meteorology.humidity == 71
    assert meteorology.native_pressure == 1015
    assert meteorology.wind_bearing == 112.5
    assert meteorology.native_wind_speed == 11
    assert meteorology.native_wind_gust_speed is None
    assert meteorology.supported_features == 0
    assert meteorology.extra_state_attributes["daily_max_wind_gust_kmh"] == 21
    assert all(entity.coordinator is coordinator for entity in entities)


async def test_partial_station_only_creates_supported_entities(hass, entry, now):
    html = '<div id="estacio">Station</div><div id="hora">16-08-2026 15:25</div><div id="temp_mit">24,1º</div>'
    make_coordinator(hass, entry, html, now)
    entities = []
    for platform in (sensor, binary_sensor, weather):
        await platform.async_setup_entry(hass, entry, entities.extend)
    assert len(entities) == 3  # temperature, observation timestamp and weather
    assert not any(isinstance(entity, binary_sensor.AvametRaining) for entity in entities)
    assert (
        next(entity for entity in entities if isinstance(entity, weather.AvametWeather)).humidity
        is None
    )


async def test_no_weather_for_rain_only_station(hass, entry, now):
    html = '<div id="estacio">Station</div><div id="hora">16-08-2026 15:25</div><div id="prec">Pluja hui 0 mm</div>'
    make_coordinator(hass, entry, html, now)
    entities = []
    await weather.async_setup_entry(hass, entry, entities.extend)
    assert entities == []


async def test_cache_only_disables_recent_rain(hass, entry, html, now):
    coordinator = make_coordinator(hass, entry, html, now)
    coordinator.data = replace(coordinator.data, from_cache=True, last_error="offline")
    entities = []
    await sensor.async_setup_entry(hass, entry, entities.extend)
    entities.extend([binary_sensor.AvametRaining(coordinator), weather.AvametWeather(coordinator)])
    with patch("custom_components.avamet.coordinator.dt_util.utcnow", return_value=now):
        for entity in entities:
            recent = entity.unique_id.endswith(
                ("rain_status", "raining", "rain_last_5_minutes_mm", "rain_last_10_minutes_mm")
            )
            assert entity.available is not recent
    assert entities[-1].condition is None
    assert entities[-1].extra_state_attributes["rain_last_10_minutes_mm"] is None


async def test_expired_reading_disables_every_entity(hass, entry, html, now):
    make_coordinator(hass, entry, html, now)
    entities = []
    for platform in (sensor, binary_sensor, weather):
        await platform.async_setup_entry(hass, entry, entities.extend)
    with patch(
        "custom_components.avamet.coordinator.dt_util.utcnow",
        return_value=now + timedelta(minutes=20),
    ):
        assert not any(entity.available for entity in entities)


async def test_diagnostics_do_not_export_private_config(hass, entry, html, now):
    make_coordinator(hass, entry, html, now)
    result = await diagnostics.async_get_config_entry_diagnostics(hass, entry)
    assert result["station_id"] == "c13m207e02"
    assert result["measurements"]["temperature_c"] == 30.1
    assert not {"token", "config_dir", "entry_id", "password"}.intersection(result)


async def test_missing_measurement_does_not_default_to_zero(hass, entry, html, now):
    coordinator = make_coordinator(hass, entry, html, now)
    entities = []
    await sensor.async_setup_entry(hass, entry, entities.extend)
    temperature = next(entity for entity in entities if entity.unique_id.endswith("temperature_c"))
    coordinator.data = Snapshot(
        replace(coordinator.data.observation, values={"humidity_percent": 70})
    )
    with patch("custom_components.avamet.coordinator.dt_util.utcnow", return_value=now):
        assert temperature.native_value is None
        assert not temperature.available


async def test_rain_enum_and_binary_semantics(hass, entry, html, now):
    coordinator = make_coordinator(hass, entry, html, now)
    text = sensor.AvametRainStatus(coordinator)
    binary = binary_sensor.AvametRaining(coordinator)
    assert text.native_value == "raining"
    assert text.options == ["raining", "dry"]
    assert binary.is_on is True
    assert binary.device_class is None
    coordinator.data = Snapshot(replace(coordinator.data.observation, rain_last_10_minutes_mm=0))
    assert text.native_value == "dry"
    assert binary.is_on is False
    coordinator.data = Snapshot(coordinator.data.observation, from_cache=True)
    assert text.native_value is None
    assert binary.is_on is None
