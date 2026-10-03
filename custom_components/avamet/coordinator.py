"""One poll per station, recent in-memory fallback and exact expiry timer."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AvametClient, AvametConnectionError, AvametHTTPError
from .const import (
    CONF_MAX_AGE,
    CONF_UPDATE_INTERVAL,
    CONF_WINDY_THRESHOLD,
    DEFAULT_MAX_AGE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_WINDY_THRESHOLD,
    DOMAIN,
)
from .models import Snapshot
from .parser import ParseError

_LOGGER = logging.getLogger(__name__)


class AvametCoordinator(DataUpdateCoordinator[Snapshot]):
    """Never refresh observation timestamps to disguise stale cached data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: AvametClient) -> None:
        self.client = client
        self.max_age_minutes = entry.options.get(CONF_MAX_AGE, DEFAULT_MAX_AGE)
        self.windy_threshold = entry.options.get(CONF_WINDY_THRESHOLD, DEFAULT_WINDY_THRESHOLD)
        self._cancel_expiry = None
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {client.station_id}",
            config_entry=entry,
            update_interval=timedelta(
                minutes=entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            ),
        )

    @property
    def observation_available(self) -> bool:
        return self.data is not None and self.data.observation.is_fresh(
            dt_util.utcnow(), self.max_age_minutes
        )

    async def _async_update_data(self) -> Snapshot:
        attempted_at = dt_util.utcnow()
        try:
            observation = await self.client.async_get_observation()
        except (AvametConnectionError, ParseError) as exc:
            # Respect rate limiting even if the most recent reading is usable.
            if isinstance(exc, AvametHTTPError) and exc.status == 429:
                raise UpdateFailed(str(exc), retry_after=exc.retry_after or 300) from exc
            if self.observation_available:
                return Snapshot(
                    self.data.observation,
                    from_cache=True,
                    last_error=str(exc),
                    attempted_at=attempted_at,
                )
            raise UpdateFailed(str(exc)) from exc
        self.cancel_expiry()
        expires = observation.observed_at + timedelta(minutes=self.max_age_minutes)
        if expires > dt_util.utcnow():
            self._cancel_expiry = async_track_point_in_utc_time(self.hass, self._expire, expires)
        return Snapshot(observation, attempted_at=attempted_at)

    @callback
    def _expire(self, now: datetime) -> None:
        self._cancel_expiry = None
        self.async_update_listeners()

    @callback
    def cancel_expiry(self) -> None:
        if self._cancel_expiry is not None:
            self._cancel_expiry()
            self._cancel_expiry = None
