"""Shared constants, independent of Home Assistant."""

DOMAIN = "avamet"
NAME = "AVAMET"
VERSION = "0.1.0"
BASE_URL = "https://www.avamet.org"
DATA_URL = BASE_URL + "/mxo_i.php?id={station_id}"
CONF_STATION_ID = "station_id"
CONF_UPDATE_INTERVAL = "update_interval_minutes"
CONF_MAX_AGE = "max_age_minutes"
CONF_WINDY_THRESHOLD = "windy_threshold_kmh"
DEFAULT_UPDATE_INTERVAL = 5
DEFAULT_MAX_AGE = 20
DEFAULT_WINDY_THRESHOLD = 40
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 8
REQUEST_ATTEMPTS = 2
USER_AGENT = "ha-avamet/0.1.0 (+https://github.com/acamposcar/ha-avamet)"
