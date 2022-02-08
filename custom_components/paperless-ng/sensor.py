"""Platform for sensor integration."""
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)

from .const import DOMAIN

import requests
import logging

_LOGGER = logging.getLogger(__name__)

STATE_ONLINE = "online"
STATE_AUTHENTICATION_FAILURE = "authentication_failure"
STATE_OFFLINE = "offline"

STATE_ATTR_DOCUMENT_TODO_TAG_NAME = "document_todo_tag_name"
STATE_ATTR_DOCUMENT_TODO_COUNT = "document_todo_count"
STATE_ATTR_DOCUMENT_TODO = "document_todo"
STATE_ATTR_DOCUMENT_TAG_COUNT = "document_tag_count"
STATE_ATTR_DOCUMENT_TOTAL_COUNT = "document_total_count"
STATE_ATTR_DOCUMENT_TAGS = "document_tags"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup Sensors"""
    async_add_entities(
        [PaperlessSensor(hass, config_entry)],
        True,
    )


class PaperlessSensor(SensorEntity):
    """Total document counter sensor"""

    def __init__(self, hass, config_entry):
        """Initialize the sensor."""
        self._state = None
        self._attr_name = (
            f"paperless-ng-{config_entry.data['host']}:{config_entry.data['port']}"
        )
        self.hass = hass
        self.base_url = f"http{'s' if config_entry.data['ssl'] else ''}://{config_entry.data['host']}:{config_entry.data['port']}/api"
        self.headers = {
            "Authorization": f"Token {config_entry.data['api_token']}",
            "Accept": "application/json",
        }
        self.todo_tag = config_entry.data.get("todo_tag")
        self.documents = None
        self.tags = None
        self.todo_documents = None

    @property
    def state(self):
        """Return state"""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return extra state attributes"""
        if not self.documents or not self.tags:
            return None
        todo_tag_obj = next(
            (el for el in self.tags.get("results") if el.get("name") == self.todo_tag),
            None,
        )
        return {
            STATE_ATTR_DOCUMENT_TODO_TAG_NAME: self.todo_tag,
            STATE_ATTR_DOCUMENT_TODO_COUNT: todo_tag_obj.get("document_count"),
            STATE_ATTR_DOCUMENT_TODO: sorted(
                self.todo_documents["results"],
                key=lambda el: el.get("created"),
            )
            if self.todo_documents
            else None,
            STATE_ATTR_DOCUMENT_TAGS: {
                el.get("id"): el.get("name") for el in self.tags.get("results")
            },
            STATE_ATTR_DOCUMENT_TAG_COUNT: {
                el.get("id"): el.get("document_count")
                for el in self.tags.get("results")
            },
            STATE_ATTR_DOCUMENT_TOTAL_COUNT: self.documents.get("count"),
        }

    def get_documents(self):
        """Gets data for all documents"""
        try:
            res = requests.get(self.base_url + "/documents/", headers=self.headers)
            return self.handle_request_status_code(res)
        except Exception as e:
            _LOGGER.error(e)
            self._state = STATE_OFFLINE

    def get_todo_documents(self, tag_id):
        """Gets data for all todo documents"""
        if not tag_id:
            return None
        try:
            res = requests.get(
                f"{self.base_url}/documents/?tags__id={tag_id}",
                headers=self.headers,
            )
            return self.handle_request_status_code(res)
        except Exception as e:
            _LOGGER.error(e)
            self._state = STATE_OFFLINE

    def get_tags(self):
        """Get tags for all documents"""
        try:
            res = requests.get(self.base_url + "/tags/", headers=self.headers)
            return self.handle_request_status_code(res)
        except Exception as e:
            _LOGGER.error(e)
            self._state = STATE_OFFLINE

    def handle_request_status_code(self, res):
        """Set state to offline/authentication failure if code isn't 200, else return json"""
        if res.status_code == 401:
            self._state = STATE_AUTHENTICATION_FAILURE
        elif res.status_code != 200:
            self._state = STATE_OFFLINE
        else:
            self._state = STATE_ONLINE
            return res.json()
        return None

    async def async_update(self):
        """Fetch data for sensor"""
        self.documents = await self.hass.async_add_executor_job(self.get_documents)
        self.tags = await self.hass.async_add_executor_job(self.get_tags)
        if self.todo_tag and self.tags:
            todo_tag_obj = next(
                (
                    el
                    for el in self.tags.get("results")
                    if el.get("name") == self.todo_tag
                ),
                None,
            )
            self.todo_documents = await self.hass.async_add_executor_job(
                self.get_todo_documents, todo_tag_obj.get("id")
            )
            if self.todo_documents:
                for doc in self.todo_documents.get("results"):
                    doc.pop("content")
