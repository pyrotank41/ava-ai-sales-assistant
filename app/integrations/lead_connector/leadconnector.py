import json
from typing import List
import httpx
import os
from datetime import datetime, timedelta

from loguru import logger
from app.integrations.lead_connector.config import CLIENT_ID, CLIENT_SECRET, TOKEN_URL
from app.integrations.lead_connector.models import LCContactInfo, LCMessage, LCMessageType
from app.integrations.lead_connector.utils import get_leadconnector_config_file
from app.integrations.lead_connector.utils import message_type_mapping

NOT_SUPPORTED_MESSAGE_TYPES = [
    LCMessageType.TYPE_CALL,
    LCMessageType.TYPE_EMAIL
    ]

class LeadConnector:
    def __init__(self, config_file=".config/leadconnector_config.json"):
        self.config_file = config_file
        self.config = get_leadconnector_config_file(config_file)

    def save_config(self):
        with open(self.config_file, "w", encoding="utf-8") as file:
            data = self.config.model_dump()
            del data["token_expiry"]
            json.dump(data, file, indent=4)

    def refresh_token(self):
        url = TOKEN_URL
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.config.refresh_token,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }

        response = httpx.post(url, data=payload)
        response_data = response.json()

        self.config.access_token = response_data["access_token"]
        self.config.refresh_token = response_data["refresh_token"]
        self.config.expires_in = int(response_data["expires_in"])
        self.config.token_expiry = datetime.now() + timedelta(
            seconds=int(response_data["expires_in"])
        )

        self.save_config()

    def make_request(self, method, url, **kwargs):
        if datetime.now() >= self.config.token_expiry:
            self.refresh_token()

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.config.access_token}"
        headers["Version"] = "2021-04-15"

        response = httpx.request(method, url, headers=headers, **kwargs)

        if response.status_code == 401:  # Token expired or unauthorized
            logger.debug("access token expired or currupted, refreshing token")
            self.refresh_token()
            headers["Authorization"] = f"Bearer {self.config.access_token}"
            response = httpx.request(method, url, headers=headers, **kwargs)

        return response

    def get_contact_info(self, contact_id: str) -> LCContactInfo:
        url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
        response = self.make_request("GET", url).json()
        logger.debug(f"Contact info response: {response}")
        return LCContactInfo(**response.get("contact"))

    def get_conversation(self, conversation_id):
        url = f"https://services.leadconnectorhq.com/conversations/{conversation_id}"
        response = self.make_request("GET", url)
        return response.json()

    def get_all_messages(
        self, conversation_id: str, limit: int = 50
    ) -> List[LCMessage]:
        url = f"https://services.leadconnectorhq.com/conversations/{conversation_id}/messages"

        # add the limit to the query params
        url += f"?limit={limit}"
        response = self.make_request("GET", url)

        resp_dict = dict(dict(response.json()).get("messages"))
        if resp_dict.get("nextPage") is True:
            logger.error("More messages available, please implement pagination")

        # sort the messages by dateAdded
        messages = [LCMessage(**message) for message in resp_dict.get("messages")]
        print("before")
        print(messages)
        
        print("after")
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
