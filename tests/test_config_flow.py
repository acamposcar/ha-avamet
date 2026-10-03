from dataclasses import replace
from unittest.mock import patch

import pytest
from homeassistant.data_entry_flow import FlowResultType, InvalidData

from custom_components.avamet.api import AvametConnectionError
from custom_components.avamet.parser import ParseError, parse_observation


async def test_user_form(hass):
    result = await hass.config_entries.flow.async_init("avamet", context={"source": "user"})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_create_normalized_station(hass, html, now):
    observation = parse_observation(html, "c13m207e02", now=now)
    with (
        patch(
            "custom_components.avamet.config_flow.AvametClient.async_get_observation",
            return_value=observation,
        ),
        patch("custom_components.avamet.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            "avamet", context={"source": "user"}, data={"station_id": " C13M207E02 "}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"] == {"station_id": "c13m207e02"}
        assert result["result"].unique_id == "c13m207e02"
        await hass.async_block_till_done()


async def test_duplicate_station_aborted_before_network(hass, entry):
    hass.config_entries._entries[entry.entry_id] = entry
    with patch("custom_components.avamet.config_flow.AvametClient.async_get_observation") as fetch:
        result = await hass.config_entries.flow.async_init(
            "avamet", context={"source": "user"}, data={"station_id": "c13m207e02"}
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    fetch.assert_not_called()


async def test_invalid_id_no_network(hass):
    with patch("custom_components.avamet.config_flow.AvametClient.async_get_observation") as fetch:
        result = await hass.config_entries.flow.async_init(
            "avamet", context={"source": "user"}, data={"station_id": "../secrets.yaml"}
        )
    assert result["errors"] == {"station_id": "invalid_station_id"}
    fetch.assert_not_called()


@pytest.mark.parametrize(
    "exception,error",
    [
        (AvametConnectionError("offline"), "cannot_connect"),
        (ParseError("bad html"), "invalid_response"),
    ],
)
async def test_flow_errors(hass, exception, error):
    with patch(
        "custom_components.avamet.config_flow.AvametClient.async_get_observation",
        side_effect=exception,
    ):
        result = await hass.config_entries.flow.async_init(
            "avamet", context={"source": "user"}, data={"station_id": "c13m207e02"}
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_options_flow(hass, entry):
    hass.config_entries._entries[entry.entry_id] = entry
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "update_interval_minutes": 10,
            "max_age_minutes": 30,
            "windy_threshold_kmh": 50,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["update_interval_minutes"] == 10


async def test_different_stations_can_be_configured(hass, html, now):
    observation = parse_observation(html, "c13m207e02", now=now)
    second = replace(observation, station_id="c24m072e02", station_name="Other station")
    with (
        patch(
            "custom_components.avamet.config_flow.AvametClient.async_get_observation",
            side_effect=[observation, second],
        ),
        patch("custom_components.avamet.async_setup_entry", return_value=True),
    ):
        first_result = await hass.config_entries.flow.async_init(
            "avamet", context={"source": "user"}, data={"station_id": "c13m207e02"}
        )
        second_result = await hass.config_entries.flow.async_init(
            "avamet", context={"source": "user"}, data={"station_id": "c24m072e02"}
        )
        await hass.async_block_till_done()
    assert first_result["type"] == second_result["type"] == FlowResultType.CREATE_ENTRY
    assert len(hass.config_entries.async_entries("avamet")) == 2


async def test_options_reject_out_of_range_values(hass, entry):
    hass.config_entries._entries[entry.entry_id] = entry
    result = await hass.config_entries.options.async_init(entry.entry_id)
    invalid = {"update_interval_minutes": 0, "max_age_minutes": 20, "windy_threshold_kmh": 40}
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(result["flow_id"], user_input=invalid)
    # Defensive validation also handles direct entry-step invocation.
    flow = hass.config_entries.options._progress[result["flow_id"]]
    result = await flow.async_step_init(invalid)
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_options"}
    assert entry.options == {}
