from dataclasses import replace
from datetime import timedelta

import pytest

from custom_components.avamet.models import Snapshot
from custom_components.avamet.parser import (
    ParseError,
    normalize_station_id,
    number,
    parse_observation,
)


def test_full_station(html, now):
    observation = parse_observation(html, "c13m207e02", now=now)
    assert observation.values == {
        "temperature_c": 30.1,
        "temperature_min_c": 21.0,
        "temperature_max_c": 31.7,
        "humidity_percent": 71.0,
        "pressure_hpa": 1015.0,
        "wind_speed_kmh": 11.0,
        "wind_direction": "ESE",
        "wind_bearing": 112.5,
        "daily_max_wind_gust_kmh": 21.0,
        "rain_today_mm": 0.0,
        "rain_month_mm": 2.8,
        "rain_year_mm": 115.7,
    }
    assert observation.rain_last_5_minutes_mm == 0
    assert observation.rain_last_10_minutes_mm == 0.2
    assert observation.observed_at.isoformat() == "2026-08-16T15:25:00+02:00"
    assert Snapshot(observation).is_raining is True
    assert observation.source_url.endswith("c13m207e02")
    with pytest.raises(TypeError):
        observation.values["temperature_c"] = 0


def test_daily_accumulated_is_not_current_rain(html, now):
    html = html.replace(",0.00]", ",3.80]").replace(",0.20]", ",3.80]")
    snapshot = Snapshot(parse_observation(html, "c13m207e02", now=now))
    assert snapshot.observation.rain_last_10_minutes_mm == 0
    assert snapshot.is_raining is False
    assert snapshot.condition(40) is None


@pytest.mark.parametrize("station_id", ["c13m207e02", "c24m072e02", "c01m001e01"])
def test_temperature_only_station(station_id, now):
    html = '<div id="estacio">Station</div><div id="hora">16-08-2026 15:25</div><div id="temp_mit">24,1º</div>'
    observation = parse_observation(html, station_id, now=now)
    assert observation.values == {"temperature_c": 24.1}
    assert observation.supports_rain is False
    assert observation.rain_error is None


def test_rain_only_station(now):
    html = '<div id="estacio">Rain gauge</div><div id="hora">16-08-2026 15:25</div><div id="prec">Pluja hui 3,8 mm</div>'
    observation = parse_observation(html, "c24m072e02", now=now)
    assert observation.values == {"rain_today_mm": 3.8}
    assert observation.supports_rain
    assert observation.rain_last_10_minutes_mm is None


@pytest.mark.parametrize(
    "text,pressure,expected",
    [
        ("1.015 hPa", True, 1015),
        ("1015,6 hPa", True, 1015.6),
        ("1015.6 hPa", True, 1015.6),
        ("1.015,6 hPa", True, 1015.6),
        ("-1,3°", False, -1.3),
        ("--", False, None),
        ("1..2", False, None),
    ],
)
def test_numeric_formats(text, pressure, expected):
    assert number(text, pressure=pressure) == expected


@pytest.mark.parametrize(
    "station", ["https://bad.example", "../config", "c13m207e02&foo=bar", "", "other", None, 123]
)
def test_invalid_ids(station):
    with pytest.raises(ValueError):
        normalize_station_id(station)


def test_id_normalization():
    assert normalize_station_id(" C13M207E02 ") == "c13m207e02"


def test_coordinates_are_not_part_of_the_device_name(html, now):
    html = html.replace(
        "IES Rafelbunyol</span>",
        "IES Rafelbunyol</span><br>39° 35' 6.21\" N, 00° 19' 54.55\" W (25 m)",
    )
    assert (
        parse_observation(html, "c13m207e02", now=now).station_name == "Rafelbunyol IES Rafelbunyol"
    )


@pytest.mark.parametrize(
    "html",
    [
        "<html></html>",
        '<div id="estacio">Station</div><div id="hora">bad date</div>',
        '<div id="estacio">Station</div><div id="hora">16-08-2026 15:25</div>',
    ],
)
def test_invalid_observation(html, now):
    with pytest.raises(ParseError):
        parse_observation(html, "c13m207e02", now=now)


@pytest.mark.parametrize(
    "change,error",
    [
        (lambda h: h.split("<script>")[0], "missing_rain_graph"),
        (lambda h: h.replace("15:25", "15:40"), "outdated_rain_graph"),
        (lambda h: h.replace("[1786893600000,0.20],", ""), "rain_graph_gap"),
        (lambda h: h.replace("1786893900000,0.20", "1786893900000,0.10"), "rain_total_decreased"),
        (lambda h: h.replace("1786893600000,0.20", "1786893600000,-1.00"), "invalid_rain_graph"),
    ],
)
def test_rain_failures_do_not_hide_measurements(html, now, change, error):
    observation = parse_observation(change(html), "c13m207e02", now=now)
    assert observation.values["temperature_c"] == 30.1
    assert observation.rain_last_10_minutes_mm is None
    assert observation.rain_error == error
    assert Snapshot(observation).is_raining is None


def test_midnight_reset(html, now):
    html = html.replace("16-08-2026 15:25", "17-08-2026 00:05")
    html = html.replace("1786893300000,0.00", "1786924500000,3.80")
    html = html.replace("1786893600000,0.20", "1786924800000,0.20")
    html = html.replace("1786893900000,0.20", "1786925100000,0.40")
    observation = parse_observation(html, "c13m207e02", now=now)
    assert observation.rain_last_10_minutes_mm == 0.4
    assert observation.rain_last_5_minutes_mm == 0.2


def test_freshness_and_future_dates(html, now):
    observation = parse_observation(html, "c13m207e02", now=now)
    assert observation.is_fresh(now, 20)
    assert not observation.is_fresh(now + timedelta(minutes=20), 20)
    assert not observation.is_fresh(now - timedelta(minutes=20), 20)


def test_cache_suppresses_current_rain(html, now):
    observation = parse_observation(html, "c13m207e02", now=now)
    snapshot = Snapshot(observation, from_cache=True)
    assert snapshot.is_raining is None
    assert snapshot.condition(40) is None
    assert snapshot.observation.observed_at == observation.observed_at


def test_condition_rain_priority_and_wind_threshold(html, now):
    observation = parse_observation(html, "c13m207e02", now=now)
    windy = replace(
        observation, values={**observation.values, "wind_speed_kmh": 40}, rain_last_10_minutes_mm=0
    )
    assert Snapshot(windy).condition(40) == "windy"
    assert Snapshot(windy).condition(41) is None
    assert Snapshot(observation).condition(1) == "rainy"


def test_span_ids_and_void_tags(now):
    html = '<section id="estacio">Test <br></br>station</section><span id="hora">16-08-2026 15:25</span><span id="temp_mit">0,0</span>'
    assert parse_observation(html, "c13m207e02", now=now).values["temperature_c"] == 0
