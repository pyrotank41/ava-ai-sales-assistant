import json
import os
import sys
from datetime import datetime, timedelta
from typing import List

import httpx
from loguru import logger

from utils.env import is_dev_env, load_env_vars
from integrations.lead_connector.config import CLIENT_ID, CLIENT_SECRET, TOKEN_URL
from integrations.lead_connector.models import (
    LCCustomField,
    LCContactInfo,
    LCMessage,
    LCMessageType,
)
from integrations.lead_connector.utils import (
    get_leadconnector_config_file,
    message_type_mapping,
    save_leadconnector_config,
)

NOT_SUPPORTED_MESSAGE_TYPES = [LCMessageType.TYPE_CALL, LCMessageType.TYPE_EMAIL]


class LeadConnector:

    def __init__(
        self,
        location_id,
    ):
        self.config = get_leadconnector_config_file()
        self.location_id = location_id

    def _refresh_token(self):
        url = TOKEN_URL
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.config.refresh_token,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }

        response = httpx.post(url, data=payload)
        response_data = response.json()

        self.config.access_token = response_data["access_token"]
        self.config.refresh_token = response_data["refresh_token"]
        self.config.expires_in = int(response_data["expires_in"])
        self.config.token_expiry = datetime.now() + timedelta(
            seconds=int(response_data["expires_in"])
        )

        save_leadconnector_config(self.config)

    def make_request(self, method, url, **kwargs):
        # if datetime.now() >= self.config.token_expiry:
        self._refresh_token()

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.config.access_token}"
        headers["Version"] = "2021-04-15"

        response = httpx.request(method, url, headers=headers, **kwargs)

        if response.status_code == 401:  # Token expired or unauthorized
            logger.debug("access token expired or currupted, refreshing token")
            self._refresh_token()
            headers["Authorization"] = f"Bearer {self.config.access_token}"
            response = httpx.request(method, url, headers=headers, **kwargs)

        return response

    def get_user_by_location(self):
        url = (
            f"https://services.leadconnectorhq.com/users/?locationId={self.location_id}"
        )
        response = self.make_request("GET", url)
        if response.status_code == 200:
            return response.json().get("users")
        else:
            response.raise_for_status()

    def get_contact_info(self, contact_id: str) -> LCContactInfo:
        url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
        response = self.make_request("GET", url).json()
        logger.debug(f"Contact info response: {response}")
        return LCContactInfo(**response.get("contact"))

    def get_contact_by_email(self, email: str) -> LCContactInfo:
        url = f"https://services.leadconnectorhq.com/contacts/"
        params = {
            "locationId": self.location_id,
            "query": email,
        }
        response = self.make_request("GET", url, params=params).json()
        logger.debug(f"Contact info response: {response}")
        return LCContactInfo(**response.get("contacts")[0])

    def get_conversation(self, conversation_id):
        url = f"https://services.leadconnectorhq.com/conversations/{conversation_id}"
        response = self.make_request("GET", url)
        return response.json()

    def search_conversations(self, contact_id: str):
        url = f"https://services.leadconnectorhq.com/conversations/search"
        params = {
            "locationId": self.location_id,
            "contactId": contact_id,
        }
        response = self.make_request("GET", url, params=params)
        logger.debug(f"Search conversations response: {response.json()}")
        return response.json().get("conversations")

    def get_conversation_id(self, contact_id: str):
        conversations = self.search_conversations(contact_id)
        if len(conversations) == 0:
            logger.error(f"No conversations found for contact {contact_id}")
            return None
        if len(conversations) > 1:
            logger.error(
                f"Multiple conversations found for contact {contact_id}. Returning the first one"
            )

        conversation_id = conversations[0].get("id")
        if isinstance(conversation_id, str):
            return conversation_id

        logger.error(f"Invalid conversation id {conversation_id}")
        raise ValueError(f"Invalid conversation id {conversation_id}")

    def get_all_messages(
        self, conversation_id: str, limit: int = 50
    ) -> List[LCMessage]:
        url = f"https://services.leadconnectorhq.com/conversations/{conversation_id}/messages"

        # add the limit to the query params
        url += f"?limit={limit}"
        response = self.make_request("GET", url)
        logger.debug(f"Get all messages response: {response.json()}")
        resp_dict = dict(dict(response.json()).get("messages"))
        if resp_dict.get("nextPage") is True:
            logger.error("More messages available, please implement pagination")

        # sort the messages by dateAdded
        messages = [LCMessage(**message) for message in resp_dict.get("messages")]
        messages = sorted(messages, key=lambda x: x.dateAdded)
        return messages

    def send_message(self, contact_id: str, message: str, message_channel: str):

        if message_channel is None:
            logger.error(f"Invalid message channel {message_channel}")
            return

        if message_channel not in message_type_mapping.values():
            logger.error(f"Invalid message channel {message_channel}")
            return

        if message_channel == "Custom":
            logger.warning(
                "Custom message channel not supported, no message will be sent"
            )
            return

        if message == "" or message is None:
            logger.error("Message cannot be empty")
            return

        if contact_id == "" or contact_id is None:
            logger.error("Contact id cannot be empty")
            return

        url = "https://services.leadconnectorhq.com/conversations/messages"
        body = {"type": message_channel, "contactId": contact_id, "message": message}

        response = self.make_request("POST", url, json=body)
        if int(response.status_code) not in [200, 201]:
            logger.error(
                f"Failed to send message to {contact_id}. Error_code: {response.status_code}\nResponse: {response.json()}"
            )
        else:
            logger.info(f"Message sent to {contact_id}. LC response: {response.json()}")

    def delete_conversation(self, conversation_id: str):
        url = f"https://services.leadconnectorhq.com/conversations/{conversation_id}"
        response = self.make_request("DELETE", url)
        if int(response.status_code) not in [200, 201]:
            logger.error(
                f"Failed to delete conversation {conversation_id}. Error_code: {response.status_code}\nResponse: {response.json()}"
            )
        else:
            logger.info(
                f"Conversation {conversation_id} deleted. LC response: {response.json()}"
            )

    def get_custom_fields(self) -> List[LCCustomField]:
        url = f"https://services.leadconnectorhq.com/locations/{self.location_id}/customFields"
        response = self.make_request("GET", url)
        data = response.json().get("customFields")

        # Convert the data to list of CustomFieldModelType
        custom_contact_fields = []
        for item in data:
            custom_contact_fields.append(LCCustomField(**item))
        # CustomFieldModelType
        return custom_contact_fields

    def get_custom_fields_id_key_mapping(self):
        custom_fields = self.get_custom_fields()
        return {field.fieldKey: field.id for field in custom_fields}


if __name__ == "__main__":
    # add current path to system path
    lc = LeadConnector(location_id="hqDwtNvswsupf6BT1Qxt")
    # CONTACT_ID = "6smJfQjKMu95Y58rIcYl"
    # conversations = lc.search_conversations(contact_id=CONTACT_ID)
    # logger.debug(json.dumps(conversations, indent=4))
    # logger.debug(f"conversation_id: {lc.get_conversation_id(contact_id=CONTACT_ID)}")
    load_env_vars()
    logger.debug(json.dumps(lc.get_user_by_location(), indent=4))
    logger.debug(lc.get_contact_by_email("karankochar13@gmail.com"))
