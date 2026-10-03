from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.avamet.api import AvametConnectionError, AvametHTTPError
from custom_components.avamet.coordinator import AvametCoordinator
from custom_components.avamet.models import Snapshot
from custom_components.avamet.parser import parse_observation


async def test_one_refresh_and_fallback(hass, entry, html, now):
    observation = parse_observation(html, "c13m207e02", now=now)
    client = Mock(
        station_id="c13m207e02", async_get_observation=AsyncMock(return_value=observation)
    )
    coordinator = AvametCoordinator(hass, entry, client)
    with patch("custom_components.avamet.coordinator.dt_util.utcnow", return_value=now):
        coordinator.data = await coordinator._async_update_data()
        assert coordinator.observation_available
        assert coordinator.data.from_cache is False
        client.async_get_observation.side_effect = AvametConnectionError("Network failed")
        fallback = await coordinator._async_update_data()
        assert fallback.from_cache is True
        assert fallback.observation is observation
        assert fallback.is_raining is None
        assert fallback.last_error == "Network failed"
        assert client.async_get_observation.await_count == 2
    coordinator.cancel_expiry()


async def test_expired_cache_is_not_used(hass, entry, html, now):
    observation = parse_observation(html, "c13m207e02", now=now)
    client = Mock(
        station_id="c13m207e02",
        async_get_observation=AsyncMock(side_effect=AvametConnectionError("Network failed")),
    )
    coordinator = AvametCoordinator(hass, entry, client)
    coordinator.data = Snapshot(observation)
    with patch(
        "custom_components.avamet.coordinator.dt_util.utcnow",
        return_value=now + timedelta(minutes=20),
    ):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_rate_limit_respected(hass, entry, html, now):
    client = Mock(
        station_id="c13m207e02",
        async_get_observation=AsyncMock(side_effect=AvametHTTPError(429, 600)),
    )
    coordinator = AvametCoordinator(hass, entry, client)
    coordinator.data = Snapshot(parse_observation(html, "c13m207e02", now=now))
    with pytest.raises(UpdateFailed) as error:
        await coordinator._async_update_data()
    assert error.value.retry_after == 600


async def test_exact_expiry_notifies_without_extra_request(hass, entry, html, now):
    observation = parse_observation(html, "c13m207e02", now=now)
    client = Mock(
        station_id="c13m207e02", async_get_observation=AsyncMock(return_value=observation)
    )
    coordinator = AvametCoordinator(hass, entry, client)
    with patch("custom_components.avamet.coordinator.dt_util.utcnow", return_value=now):
        coordinator.data = await coordinator._async_update_data()
    assert coordinator._cancel_expiry is not None
    coordinator.cancel_expiry()
    with patch.object(coordinator, "async_update_listeners") as notify:
        coordinator._expire(now + timedelta(minutes=20))
        notify.assert_called_once()
    assert client.async_get_observation.await_count == 1


async def test_options(hass, entry):
    hass.config_entries._entries[entry.entry_id] = entry
    hass.config_entries.async_update_entry(
        entry,
        options={"update_interval_minutes": 10, "max_age_minutes": 30, "windy_threshold_kmh": 50},
    )
    coordinator = AvametCoordinator(hass, entry, Mock(station_id="c13m207e02"))
    assert coordinator.update_interval == timedelta(minutes=10)
    assert coordinator.max_age_minutes == 30
    assert coordinator.windy_threshold == 50


async def test_old_successful_response_is_unavailable(hass, entry, html, now):
    observation = parse_observation(html, "c13m207e02", now=now)
    client = Mock(
        station_id="c13m207e02", async_get_observation=AsyncMock(return_value=observation)
    )
    coordinator = AvametCoordinator(hass, entry, client)
    with patch(
        "custom_components.avamet.coordinator.dt_util.utcnow", return_value=now + timedelta(hours=1)
    ):
        coordinator.data = await coordinator._async_update_data()
        assert not coordinator.observation_available
        assert coordinator._cancel_expiry is None


async def test_expiry_uses_elapsed_time_across_dst_change(hass, entry, html, now):
    observation = parse_observation(html, "c13m207e02", now=now)
    observed = observation.observed_at.replace(year=2026, month=10, day=25, hour=2, minute=55)
    observation = replace(observation, observed_at=observed)
    current = datetime(2026, 10, 25, 0, 56, tzinfo=UTC)
    client = Mock(
        station_id="c13m207e02", async_get_observation=AsyncMock(return_value=observation)
    )
    coordinator = AvametCoordinator(hass, entry, client)
    with (
        patch("custom_components.avamet.coordinator.dt_util.utcnow", return_value=current),
        patch("custom_components.avamet.coordinator.async_track_point_in_utc_time") as schedule,
    ):
        await coordinator._async_update_data()
    expiry = schedule.call_args.args[2]
    assert expiry == datetime(2026, 10, 25, 1, 15, tzinfo=UTC)
    assert expiry.tzinfo is UTC
    coordinator.cancel_expiry()
