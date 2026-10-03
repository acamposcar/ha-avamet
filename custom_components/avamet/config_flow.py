"""UI configuration, unique station IDs and reloadable options."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AvametClient, AvametConnectionError
from .const import (
    CONF_MAX_AGE,
    CONF_STATION_ID,
    CONF_UPDATE_INTERVAL,
    CONF_WINDY_THRESHOLD,
    DEFAULT_MAX_AGE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_WINDY_THRESHOLD,
    DOMAIN,
)
from .parser import ParseError, normalize_station_id


class AvametConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """One configuration entry per public station."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors = {}
        if user_input is not None:
            try:
                station_id = normalize_station_id(user_input[CONF_STATION_ID])
            except ValueError, TypeError, KeyError:
                errors[CONF_STATION_ID] = "invalid_station_id"
            else:
                await self.async_set_unique_id(station_id)
                self._abort_if_unique_id_configured()
                try:
                    observation = await AvametClient(
                        async_get_clientsession(self.hass), station_id
                    ).async_get_observation()
                except AvametConnectionError:
                    errors["base"] = "cannot_connect"
                except ParseError:
                    errors["base"] = "invalid_response"
                else:
                    return self.async_create_entry(
                        title=observation.station_name, data={CONF_STATION_ID: station_id}
                    )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_STATION_ID): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AvametOptionsFlow()


class AvametOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
                vol.Required(
                    CONF_MAX_AGE, default=options.get(CONF_MAX_AGE, DEFAULT_MAX_AGE)
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=120)),
                vol.Required(
                    CONF_WINDY_THRESHOLD,
                    default=options.get(CONF_WINDY_THRESHOLD, DEFAULT_WINDY_THRESHOLD),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=200)),
            }
        )
        errors = {}
        if user_input is not None:
            try:
                validated = schema(user_input)
            except vol.Invalid:
                errors["base"] = "invalid_options"
            else:
                return self.async_create_entry(title="", data=validated)
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
