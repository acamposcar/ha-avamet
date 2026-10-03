"""Parse AVAMET's public HTML without depending on its CSS layout.

The page is still HTML, not a documented anonymous API. Measurements are
optional: a rain-only or temperature-only station must not fail because it
does not have a barometer, anemometer or a second wind measurement.
"""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

from .models import Observation

LOCAL_TIMEZONE = ZoneInfo("Europe/Madrid")
STATION_ID_PATTERN = re.compile(r"c\d{2}m\d{3}e\d{2}\Z")
CAPTURED_IDS = {
    "estacio",
    "hora",
    "temp_mit",
    "temp_min",
    "temp_max",
    "hrel",
    "pres",
    "vent",
    "prec",
}
VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
BEARINGS = {
    name: index * 22.5
    for index, name in enumerate(
        (
            "N",
            "NNE",
            "NE",
            "ENE",
            "E",
            "ESE",
            "SE",
            "SSE",
            "S",
            "SSW",
            "SW",
            "WSW",
            "W",
            "WNW",
            "NW",
            "NNW",
        )
    )
}
BEARINGS.update({name.replace("W", "O"): value for name, value in tuple(BEARINGS.items())})


class ParseError(ValueError):
    """The response does not contain a usable station observation."""


def normalize_station_id(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Station ID must be a string")
    station_id = value.strip().lower()
    if not STATION_ID_PATTERN.fullmatch(station_id):
        raise ValueError("Expected an AVAMET station ID such as c13m207e02")
    return station_id


class ObservationParser(HTMLParser):
    """Extract text blocks by stable element IDs, preserving repeated blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: dict[str, list[str]] = {}
        self._captures: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in VOID_ELEMENTS:
            if tag == "br":
                self.handle_data(" ")
            return
        for capture in self._captures:
            capture["depth"] += 1
        element_id = dict(attrs).get("id")
        if element_id in CAPTURED_IDS:
            self._captures.append({"id": element_id, "depth": 1, "text": []})

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in VOID_ELEMENTS:
            if tag == "br":
                self.handle_data(" ")
        else:
            self.handle_starttag(tag, attrs)
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_ELEMENTS:
            return
        for capture in self._captures[:]:
            capture["depth"] -= 1
            if capture["depth"] == 0:
                text = " ".join("".join(capture["text"]).split())
                self.values.setdefault(capture["id"], []).append(text)
                self._captures.remove(capture)

    def handle_data(self, data: str) -> None:
        for capture in self._captures:
            capture["text"].append(data)


def number(text: str, *, pressure: bool = False) -> float | None:
    """Handle European separators and placeholders, not missing-value zeroes."""
    match = re.search(r"-?\d[\d.,]*", text)
    if match is None:
        return None
    raw = match.group()
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif pressure and re.fullmatch(r"\d{1,2}\.\d{3}", raw):
        raw = raw.replace(".", "")
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def precipitation_series(html: str) -> list[tuple[datetime, float]]:
    """AVAMET encodes Madrid wall time inside UTC-looking graph timestamps."""
    graph_start = html.find("$('#grafic4').highcharts")
    if graph_start < 0:
        raise ParseError("missing_rain_graph")
    match = re.search(
        r"series:\s*\[\{.*?data:\s*\[(.*?)\]\s*,\s*color:.*?name:\s*['\"]Precipitaci(?:ó|&oacute;)n?['\"]",
        html[graph_start:],
        re.DOTALL,
    )
    if match is None:
        raise ParseError("invalid_rain_graph")
    points: dict[datetime, float] = {}
    for raw_stamp, raw_amount in re.findall(r"\[(\d{13}),\s*(-?\d+(?:\.\d+)?)\]", match[1]):
        stamp = datetime.fromtimestamp(int(raw_stamp) / 1000, UTC).replace(tzinfo=LOCAL_TIMEZONE)
        amount = float(raw_amount)
        if not math.isfinite(amount) or amount < 0 or (stamp in points and points[stamp] != amount):
            raise ParseError("invalid_rain_graph")
        points[stamp] = amount
    if not points:
        raise ParseError("empty_rain_graph")
    return sorted(points.items())


def rainfall_window(
    series: list[tuple[datetime, float]], observed_at: datetime, minutes: int
) -> float:
    """Difference daily totals, reject gaps and account for midnight reset."""
    end = observed_at.astimezone(UTC)
    cutoff = end - timedelta(minutes=minutes)
    eligible = [(stamp, amount) for stamp, amount in series if stamp.astimezone(UTC) <= end]
    baseline = [
        index for index, (stamp, _) in enumerate(eligible) if stamp.astimezone(UTC) <= cutoff
    ]
    if not baseline:
        raise ParseError("insufficient_rain_history")
    window = eligible[baseline[-1] :]
    if (end - window[-1][0].astimezone(UTC)).total_seconds() > 120 or (
        cutoff - window[0][0].astimezone(UTC)
    ).total_seconds() > 120:
        raise ParseError("outdated_rain_graph")
    total = 0.0
    for (previous_at, previous), (stamp, current) in zip(window, window[1:], strict=False):
        gap = (stamp.astimezone(UTC) - previous_at.astimezone(UTC)).total_seconds()
        if not 0 < gap <= 7 * 60:
            raise ParseError("rain_graph_gap")
        if stamp.date() != previous_at.date():
            total += current
        elif current >= previous:
            total += current - previous
        else:
            raise ParseError("rain_total_decreased")
    return round(total, 2)


def parse_observation(html: str, station_id: str, *, now: datetime | None = None) -> Observation:
    """Require station identity and date, but allow any subset of measurements."""
    station_id = normalize_station_id(station_id)
    parser = ObservationParser()
    parser.feed(html)
    parser.close()
    blocks = parser.values
    try:
        name = blocks["estacio"][0].strip()
        # Coordinates are appended inside the same block, but are not a name.
        coordinate = re.search(r"\s+\d{1,2}°\s*\d{1,2}'\s*[\d.]+[\"″]\s*[NS]", name)
        if coordinate:
            name = name[: coordinate.start()].strip()
        observed = datetime.strptime(blocks["hora"][0], "%d-%m-%Y %H:%M").replace(
            tzinfo=LOCAL_TIMEZONE
        )
    except (KeyError, IndexError, ValueError) as exc:
        raise ParseError("missing_station_or_timestamp") from exc
    if not name:
        raise ParseError("missing_station_name")
    values: dict[str, float | str] = {}
    for block, key in (
        ("temp_mit", "temperature_c"),
        ("temp_min", "temperature_min_c"),
        ("temp_max", "temperature_max_c"),
        ("hrel", "humidity_percent"),
        ("pres", "pressure_hpa"),
    ):
        value = number(blocks.get(block, [""])[0], pressure=block == "pres")
        if value is not None and (block != "hrel" or 0 <= value <= 100):
            values[key] = value
    for item in blocks.get("vent", []):
        value = number(item)
        if value is None or value < 0:
            continue
        if any(label in item.casefold() for label in ("màx", "máx", "max")):
            values["daily_max_wind_gust_kmh"] = value
        else:
            values["wind_speed_kmh"] = value
            direction = re.search(r"km/h\s+([A-Z]+)\b", item, re.IGNORECASE)
            if direction and direction[1].upper() in BEARINGS:
                values["wind_direction"] = direction[1].upper()
                values["wind_bearing"] = BEARINGS[direction[1].upper()]
    for item in blocks.get("prec", []):
        for label, key in (
            ("hui", "rain_today_mm"),
            ("mensual", "rain_month_mm"),
            ("anual", "rain_year_mm"),
        ):
            if label in item.casefold() and (value := number(item)) is not None and value >= 0:
                values[key] = value
    if not values:
        raise ParseError("no_measurements")
    rain_5 = rain_10 = None
    rain_error = None
    if "rain_today_mm" in values:
        try:
            series = precipitation_series(html)
            rain_10 = rainfall_window(series, observed, 10)
            try:
                rain_5 = rainfall_window(series, observed, 5)
            except ParseError:
                pass
        except (ParseError, ValueError, OverflowError, OSError) as exc:
            rain_error = str(exc) if isinstance(exc, ParseError) else "invalid_rain_graph"
    return Observation(
        station_id, name, observed, now or datetime.now(UTC), values, rain_5, rain_10, rain_error
    )
