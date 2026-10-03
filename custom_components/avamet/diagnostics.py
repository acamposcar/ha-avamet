"""Public station diagnostics; never export Home Assistant config or tokens."""


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    snapshot = coordinator.data
    observation = snapshot.observation
    return {
        "station_id": observation.station_id,
        "station_name": observation.station_name,
        "observed_at": observation.observed_at.isoformat(),
        "fetched_at": observation.fetched_at.isoformat(),
        "attempted_at": snapshot.attempted_at.isoformat(),
        "available": coordinator.last_update_success and coordinator.observation_available,
        "from_cache": snapshot.from_cache,
        "last_error": snapshot.last_error,
        "rain_error": observation.rain_error,
        "measurements": dict(observation.values),
        "rain_last_10_minutes_mm": None
        if snapshot.from_cache
        else observation.rain_last_10_minutes_mm,
        "options": dict(entry.options),
    }
