from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.util import dt as dt_util

from custom_components.avamet.api import AvametConnectionError
from custom_components.avamet.parser import parse_observation


async def test_real_entry_setup_registers_and_unloads_entities(hass, entry, html, now):
    observation = parse_observation(html, "c13m207e02", now=now)
    observation = replace(observation, observed_at=dt_util.utcnow() - timedelta(minutes=5))
    hass.config_entries._entries[entry.entry_id] = entry
    with patch(
        "custom_components.avamet.api.AvametClient.async_get_observation", return_value=observation
    ) as fetch:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        states = [state for state in hass.states.async_all() if "avamet" in state.entity_id]
        assert len(states) == 17
        assert all(state.state not in ("unknown", "unavailable") for state in states)
        assert fetch.await_count == 1
        meteorology = next(state for state in states if state.entity_id.startswith("weather."))
        assert meteorology.state == "rainy"
        assert meteorology.attributes["temperature"] == 30.1
        assert "wind_gust_speed" not in meteorology.attributes
        assert entry.runtime_data._cancel_expiry is not None
        coordinator = entry.runtime_data
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert coordinator._cancel_expiry is None
        assert all(
            hass.states.get(state.entity_id) is None
            or hass.states.get(state.entity_id).state == "unavailable"
            for state in states
        )


async def test_initial_failure_uses_home_assistant_setup_retry(hass, entry):
    hass.config_entries._entries[entry.entry_id] = entry
    with patch(
        "custom_components.avamet.api.AvametClient.async_get_observation",
        side_effect=AvametConnectionError("offline"),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state == ConfigEntryState.SETUP_RETRY
        assert not any("avamet" in state.entity_id for state in hass.states.async_all())
