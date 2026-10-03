"""Tests run against real Home Assistant classes, without production config."""

from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from unittest.mock import Mock

import pytest
from homeassistant import config_entries, loader
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry, device_registry, entity_registry, frame

COMPONENT_ROOT = Path(__file__).resolve().parents[1] / "custom_components"

SAMPLE_HTML = """
<div id="estacio">Rafelbunyol <br><span>IES Rafelbunyol</span></div>
<div id="hora">16-08-2026 15:25</div>
<div id="temp_mit">30,1&deg;</div>
<div id="temp_min"><span>mín </span>21,0&deg;</div>
<div id="temp_max"><span>màx </span>31,7&deg;</div>
<div id="hrel">Humitat<br/>71%</div>
<div id="pres">Pressió al nivell de la mar<br/>1.015 hPa</div>
<div id="vent">Vent<br/>11 km/h ESE</div>
<div id="vent">Vent màx<br/>21 km/h</div>
<div id="prec">Pluja hui<br/>0,0 mm</div>
<div id="prec">Pluja mensual<br/>2,8 mm</div>
<div id="prec">Pluja anual<br/>115,7 mm</div>
<script>$('#grafic4').highcharts({
series:[{yAxis:0,data:[[1786893300000,0.00],[1786893600000,0.20],
[1786893900000,0.20]],color:'#0088ff',name:'Precipitació'}]});</script>
"""


@pytest.fixture
def html():
    return SAMPLE_HTML


@pytest.fixture
def now():
    return datetime(2026, 8, 16, 13, 30, tzinfo=UTC)


@pytest.fixture
async def hass(tmp_path, monkeypatch):
    (tmp_path / "custom_components").symlink_to(COMPONENT_ROOT, target_is_directory=True)
    instance = HomeAssistant(str(tmp_path))
    instance.config.skip_pip = True
    instance.config.time_zone = "Europe/Madrid"
    instance.config_entries = config_entries.ConfigEntries(instance, {})
    loader.async_setup(instance)
    frame.async_setup(instance)
    await instance.config_entries.async_initialize()
    await area_registry.async_load(instance)
    device_registry.async_setup(instance)
    await device_registry.async_load(instance)
    await entity_registry.async_load(instance)
    session = Mock()
    monkeypatch.setattr(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        lambda *args, **kwargs: session,
    )
    monkeypatch.setattr(
        "custom_components.avamet.config_flow.async_get_clientsession",
        lambda *args, **kwargs: session,
    )
    yield instance
    await instance.async_stop(force=True)
    await instance.async_block_till_done()


@pytest.fixture
def entry():
    return config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain="avamet",
        title="Test station",
        data={"station_id": "c13m207e02"},
        options={},
        source="user",
        unique_id="c13m207e02",
        discovery_keys=MappingProxyType({}),
        subentries_data=(),
    )
