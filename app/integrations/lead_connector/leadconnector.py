import json
from datetime import datetime, timedelta
from typing import List, Optional

import httpx
from loguru import logger

from utils.env import load_env_vars
from integrations.lead_connector.config import CLIENT_ID, CLIENT_SECRET, TOKEN_URL
from integrations.lead_connector.models import (
    LCCustomField,
    LCContactInfo,
    LCMessage,
    LCMessageType,
)
from integrations.lead_connector.utils import (
    get_leadconnector_config_file,
    get_message_channel,
    message_type_mapping,
    save_leadconnector_config,
)

NOT_SUPPORTED_MESSAGE_TYPES = [LCMessageType.TYPE_CALL, LCMessageType.TYPE_EMAIL]

class NoConversationFoundError(Exception):
    pass

class LeadConnector:

    def __init__(
        self,
        location_id,
    ):
        self.config = get_leadconnector_config_file()
        self.location_id = location_id
        # valide the location id
        if self.location_id is None:
            logger.error("Location id cannot be empty or None")
            raise ValueError("Location id cannot be empty or None")

        try:
            self.location_info = self.get_subaccount(self.location_id)
        except Exception as e:
            logger.error(f"Error while getting subaccount: {str(e)}")
            raise e

    def get_subaccount(self, location_id):
        if location_id is None:
            logger.error("Location id cannot be empty")
            raise ValueError("Location id cannot be empty")
        url = f"https://services.leadconnectorhq.com/locations/{location_id}"
        response = self.make_request("GET", url)
        self.subaccount = response.json().get("location")
        return self.subaccount

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

        logger.debug(f"Making request to {url}")
        response = httpx.request(method, url, headers=headers, **kwargs)

        if response.status_code == 401:  # Token expired or unauthorized
            logger.debug("access token expired or currupted, refreshing token")
            self._refresh_token()
            headers["Authorization"] = f"Bearer {self.config.access_token}"
            response = httpx.request(method, url, headers=headers, **kwargs)

        response.raise_for_status()

        return response

    def get_user_by_location(self):
        url = (
            f"https://services.leadconnectorhq.com/users/?locationId={self.location_id}"
        )
        response = self.make_request("GET", url)
        return response.json().get("users")

    def get_contact_info(self, contact_id: str) -> Optional[LCContactInfo]:
        url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
        response = self.make_request("GET", url)
        logger.debug(f"Contact info response: {response.json()}")

        contact_data = response.json().get("contact")
        if not contact_data:
            logger.error(f"Unexpected response format: {response.json()}")
            raise ValueError("Unexpected response format")

        return LCContactInfo(**contact_data)

    def get_contact_by_email(self, email: str) -> LCContactInfo:
        url = f"https://services.leadconnectorhq.com/contacts/"
        params = {
            "locationId": self.location_id,
            "query": email,
        }
        response = self.make_request("GET", url, params=params).json()
        logger.debug(f"Contact info response: {response}")
        return LCContactInfo(**response.get("contacts")[0])

    def update_contact(self, contact_id: str, data: dict):
        if contact_id is None:
            logger.error("Contact id cannot be empty")
            raise ValueError("Contact id cannot be empty")
        if data is None:
            logger.error("Data cannot be empty")
            raise ValueError("Data cannot be empty")

        url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
        response = self.make_request("PUT", url, json=data)
        logger.debug(f"Update contact response: {response.json()}")
        return response.json().get("contact")

    def updated_contact_custom_field_value(
        self,
        contact_id: str,
        value: str,
        custom_field_key: Optional[str] = None,
        custom_field_id: Optional[str] = None,
    ):
        if custom_field_key is None and custom_field_id is None:
            logger.error("Custom field key or id must be provided")
            raise ValueError("Custom field key or id must be provided")

        if custom_field_id is None:
            update_data = {
                "customFields": [{"key": custom_field_key, "value": value}]
            }
        else:
            update_data = {
                "customFields": [{"id": custom_field_id, "value": value}]
            }

        logger.info(f"Updating custom field data:{json.dumps(update_data, indent=4)} ")

        return self.update_contact(contact_id, update_data)

    def update_contact_tags(self, contact_id: str, tags: List[str]):
        if contact_id is None:
            logger.error("Contact id cannot be empty")
            raise ValueError("Contact id cannot be empty")
        if tags is None:
            logger.error("Tags cannot be empty")
            raise ValueError("Tags cannot be empty")

        body = {"tags": tags}
        return self.update_contact(contact_id, body)

    def add_tag_to_contact(self, contact_id: str, tag: str):
        contact_info = self.get_contact_info(contact_id)
        contact_info.tags.append(tag)
        tags = contact_info.tags
        return self.update_contact_tags(contact_id=contact_id, tags=tags)
    
    def remove_tag_from_contact(self, contact_id: str, tag: str):
        contact_info = self.get_contact_info(contact_id)
        contact_info.tags.remove(tag)
        tags = contact_info.tags
        return self.update_contact_tags(contact_id=contact_id, tags=tags)

    def get_conversation(self, conversation_id):
        url = f"https://services.leadconnectorhq.com/conversations/{conversation_id}"
        response = self.make_request("GET", url)
        return response.json()

    def search_conversations(self, contact_id: str):
        if contact_id is None:
            logger.error("Contact id cannot be empty")
            raise ValueError("Contact id cannot be empty")

        url = f"https://services.leadconnectorhq.com/conversations/search"
        params = {
            "locationId": self.location_id,
            "contactId": contact_id,
        }
        response = self.make_request("GET", url, params=params)
        logger.debug(f"Search conversations response: {response.json()}")
        return response.json().get("conversations")

    def get_conversation_id(self, contact_id: str):
        if contact_id is None:
            logger.error("Contact id cannot be empty")
            raise ValueError("Contact id cannot be empty")

        conversations = self.search_conversations(contact_id)

        if len(conversations) == 0:
            raise NoConversationFoundError(f"No conversations found for contact {contact_id}")
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

        if conversation_id is None:
            raise ValueError("Conversation id cannot be empty")
        if isinstance(limit, int) is False:
            raise ValueError("Limit must be an integer")

        url = f"https://services.leadconnectorhq.com/conversations/{conversation_id}/messages"

        # add the limit to the query params
        url += f"?limit={limit}"
        response = self.make_request("GET", url)
        logger.debug(f"Get all messages response: {response.json()}")
        resp_dict = dict(dict(response.json()).get("messages"))
        if resp_dict.get("nextPage") is True:
            logger.warning("More messages available, please implement pagination")

        # sort the messages by dateAdded
        messages = [LCMessage(**message) for message in resp_dict.get("messages")]
        messages = sorted(messages, key=lambda x: x.dateAdded)
        return messages

    def send_message(self, contact_id: str, message: str, message_channel: str):

        if message_channel is None:
            logger.error(f"Invalid message channel {message_channel}")
            raise ValueError("Message channel cannot be None")

        if message_channel not in message_type_mapping.values():
            logger.error(f"Invalid message channel {message_channel}")
            raise ValueError("Invalid message channel")

        if message_channel == "Custom":
            logger.warning(
                "Custom message channel not supported, no message will be sent"
            )
            raise  ValueError("Custom message channel not supported")

        if message == "" or message is None:
            logger.error("Message cannot be empty")
            raise ValueError("Message cannot be empty or None")

        if contact_id == "" or contact_id is None:
            logger.error("Contact id cannot be empty")
            raise ValueError("Contact id cannot be empty, None")

        url = "https://services.leadconnectorhq.com/conversations/messages"
        body = {"type": message_channel, "contactId": contact_id, "message": message}

        response = self.make_request("POST", url, json=body)
        if int(response.status_code) not in [200, 201]:
            logger.error(
                f"Failed to send message to {contact_id}. Error_code: {response.status_code}\nResponse: {response.json()}"
            )
        else:
            logger.info(f"Message sent to {contact_id}. LC response: {response.json()}")
            return response.json().get("message")

    def delete_conversation(self, conversation_id: str):

        if conversation_id is None:
            logger.error("Conversation id cannot be empty")
            raise ValueError("Conversation id cannot be empty")

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
            return response.json()

    def create_conversation(self, contact_id: str):

        if contact_id is None:
            logger.error("Contact id cannot be empty")
            raise ValueError("Contact id cannot be empty")

        # by default ghl doesnt create a conversation, if the conversation is not created, the messages will not be sent
        url = "https://services.leadconnectorhq.com/conversations/"

        body = {
            "locationId": self.location_id, 
            "contactId": contact_id
            }
        response = self.make_request("POST", url, json=body)
        logger.info(f"Create conversation response: {response.json()}")
        return response.json().get("conversation")

    def get_custom_fields(self) -> List[LCCustomField]:

        url = f"https://services.leadconnectorhq.com/locations/{self.location_id}/customFields"
        response = self.make_request("GET", url)
        data = response.json().get("customFields")

        try:
            # Convert the data to list of CustomFieldModelType
            custom_contact_fields = []
            for item in data:
                custom_contact_fields.append(LCCustomField(**item))
            # CustomFieldModelType
            return custom_contact_fields

        except Exception as e:
            logger.error(f"response code: {response.status_code}")
            logger.error(f"Error while getting custom fields: {str(e)}")
            raise e

    def get_custom_fields_id_key_mapping(self):
        custom_fields = self.get_custom_fields()
        return {field.fieldKey: field.id for field in custom_fields}


if __name__ == "__main__":
    # add current path to system path
    lc = LeadConnector(location_id="hqDwtNvswsupf6BT1Qxt")

    # hqDwtNvswsupf6BT1Qxt
    # CONTACT_ID = "6smJfQjKMu95Y58rIcYl"
    # conversations = lc.search_conversations(contact_id=CONTACT_ID)
    # logger.debug(json.dumps(conversations, indent=4))
    # logger.debug(f"conversation_id: {lc.get_conversation_id(contact_id=CONTACT_ID)}")
    load_env_vars()
    # logger.debug(json.dumps(lc.get_user_by_location(), indent=4))
    # logger.debug(lc.get_contact_by_email("karankochar13@gmail.com"))

    # test add and remove tag
    #
    # print(lc.add_tag_to_contact("mmprUyomgvUt0m3R5PLu", "test_tag"))
    # print(lc.add_tag_to_contact("mmprUyomgvUt0m3R5PLu", "test_tag"))

    contact_id = "MpgcABL9Hc3nUd0fTWwY"
    resp = lc.get_all_messages(conversation_id=lc.get_conversation_id(contact_id=contact_id))

    for message in resp:
        message_type = message.messageType
        logger.info(message.body)
        logger.debug(get_message_channel(message_type))

    # print(lc.remove_tag_from_contact("mmprUyomgvUt0m3R5PLu", "test_tag"))
