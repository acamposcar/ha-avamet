"""Immutable observations and transport status; no Home Assistant dependency."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from types import MappingProxyType

from .const import DATA_URL


@dataclass(frozen=True, slots=True)
class Observation:
    """Values from a single station observation, never merged with older data."""

    station_id: str
    station_name: str
    observed_at: datetime
    fetched_at: datetime
    values: Mapping[str, float | str]
    rain_last_5_minutes_mm: float | None = None
    rain_last_10_minutes_mm: float | None = None
    rain_error: str | None = None

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None or self.fetched_at.tzinfo is None:
            raise ValueError("Observation timestamps must include a timezone")
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))

    @property
    def source_url(self) -> str:
        return DATA_URL.format(station_id=self.station_id)

    @property
    def supports_rain(self) -> bool:
        return "rain_today_mm" in self.values or self.rain_last_10_minutes_mm is not None

    def is_fresh(self, now: datetime, max_age_minutes: int) -> bool:
        age = now - self.observed_at
        return timedelta(minutes=-5) <= age < timedelta(minutes=max_age_minutes)


@dataclass(frozen=True, slots=True)
class Snapshot:
    """Transport metadata does not change the observation's original dates."""

    observation: Observation
    from_cache: bool = False
    last_error: str | None = None
    attempted_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_raining(self) -> bool | None:
        rain = self.observation.rain_last_10_minutes_mm
        return None if self.from_cache or rain is None else rain > 0

    def condition(self, windy_threshold: float) -> str | None:
        if self.is_raining is None:
            return None
        if self.is_raining:
            return "rainy"
        wind = self.observation.values.get("wind_speed_kmh")
        if isinstance(wind, (int, float)) and wind >= windy_threshold:
            return "windy"
        return None
