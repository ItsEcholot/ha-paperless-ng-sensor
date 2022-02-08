"""Config flow for Paperless NG integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import requests

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Required("port", default="8000"): str,
        vol.Required("ssl", default=False): bool,
        vol.Required("username"): str,
        vol.Required("password"): str,
        vol.Optional("todo_tag"): str,
    }
)


class ConfigurationHub:
    """Stores and requests API token to access Paperless-NG API"""

    def __init__(self, host: str, port: str, ssl: bool) -> None:
        self.host = host
        self.port = port
        self.ssl = ssl
        self.api_token = None
        self.todo_tag = None

    def authenticate(self, username: str, password: str) -> bool:
        """Uses username and password to request an API token from Paperless-NG"""
        url = f"http{'s' if self.ssl else ''}://{self.host}:{self.port}/api/token/"
        headers = {"Accept": "application/json"}
        res = requests.post(
            url, headers=headers, data={"username": username, "password": password}
        )
        if res.status_code == 403:
            _LOGGER.debug(
                "Got code 403, probably invalid credentials:\n%s\n%s",
                res.raw,
                res.headers,
            )
            raise InvalidAuth
        if res.status_code != 200:
            _LOGGER.debug(
                "Expected 200, got %i:\n%s\n%s",
                res.status_code,
                res.raw,
                res.headers,
            )
            raise CannotConnect
        if res.headers["Content-Type"] != "application/json":
            _LOGGER.debug(
                "Expected content-type to be 'application/json' got '%s'",
                res.headers["Content-Type"],
            )
            raise InvalidAuth
        try:
            self.api_token = res.json()["token"]
            _LOGGER.debug("Received API Key for Paperless-NG")
        except requests.exceptions.JSONDecodeError as json_decode_error:
            raise InvalidAuth from json_decode_error
        return True

    def get_token(self) -> str:
        """Returns api token"""
        return self.api_token


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate the user input allows us to connect.
    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    hub = ConfigurationHub(data["host"], data["port"], data["ssl"])

    if not await hass.async_add_executor_job(
        hub.authenticate, data["username"], data["password"]
    ):
        raise InvalidAuth

    # Return info that you want to store in the config entry.
    return {
        "title": f"Paperless-NG {data['host']}:{data['port']}",
        "api_token": hub.get_token(),
        "todo_tag": data["todo_tag"],
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Paperless NG."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(info["api_token"])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=info["title"],
                data={
                    "host": user_input["host"],
                    "port": user_input["port"],
                    "ssl": user_input["ssl"],
                    "api_token": info["api_token"],
                    "todo_tag": info["todo_tag"],
                },
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
