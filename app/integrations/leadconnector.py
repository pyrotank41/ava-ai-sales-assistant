import json
import httpx
import os
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from httpx import AsyncClient
from loguru import logger

from app.config import PERMISSION_TAG


CLIENT_ID = os.getenv("LEADCONNECTOR_CLIENT_ID")
CLIENT_SECRET = os.getenv("LEADCONNECTOR_CLIENT_SECRET")
REDIRECT_URI = os.getenv("LEADCONNECTOR_REDIRECT_URI")
AUTHORIZATION_URL = "https://marketplace.leadconnectorhq.com/oauth/chooselocation"
TOKEN_URL = "https://services.leadconnectorhq.com/oauth/token"  # url to get the token using the code from the authorization url

SCOPE = """
calendars.write
calendars.readonly
contacts.readonly
contacts.write
oauth.write
oauth.readonly
workflows.readonly
calendars/events.readonly
calendars/events.write
conversations.write
conversations.readonly
conversations/message.readonly
conversations/message.write
snapshots.readonly
users.write
users.readonly
surveys.readonly
opportunities.write
opportunities.readonly
medias.readonly
medias.write
locations/tags.write
locations/templates.readonly
locations/tags.readonly
locations/tasks.write
locations/tasks.readonly
locations/customFields.readonly
locations/customFields.write
businesses.readonly
businesses.write
calendars/groups.readonly
calendars/groups.write
campaigns.readonly
forms.readonly
forms.write
links.readonly
links.write
locations.write
locations.readonly
locations/customValues.readonly
locations/customValues.write
"""


from pydantic import BaseModel, HttpUrl
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


# Define an Enum for message types
class LCMessageType(
    int, Enum
):  # the type we get from the leadconnector get all message api
    TYPE_CALL = 1
    TYPE_SMS = 2
    TYPE_EMAIL = 3
    TYPE_FACEBOOK = 4
    TYPE_GMB = 5
    TYPE_INSTAGRAM = 6
    TYPE_WHATSAPP = 7
    TYPE_ACTIVITY_CONTACT = 8
    TYPE_ACTIVITY_INVOICE = 9
    TYPE_ACTIVITY_PAYMENT = 10
    TYPE_ACTIVITY_OPPORTUNITY = 11
    TYPE_LIVE_CHAT = 12
    TYPE_ACTIVITY_APPOINTMENT = 13


message_type_mapping = {  # the mapping of the message type required when sending a message
        LCMessageType.TYPE_CALL: "Custom",
        LCMessageType.TYPE_SMS: "SMS",
        LCMessageType.TYPE_EMAIL: "Email",
        LCMessageType.TYPE_FACEBOOK: "FB",
        LCMessageType.TYPE_GMB: "GMB",
        LCMessageType.TYPE_INSTAGRAM: "IG",
        LCMessageType.TYPE_WHATSAPP: "WhatsApp",
        LCMessageType.TYPE_ACTIVITY_CONTACT: "Custom",
        LCMessageType.TYPE_ACTIVITY_INVOICE: "Custom",
        LCMessageType.TYPE_ACTIVITY_PAYMENT: "Custom",
        LCMessageType.TYPE_ACTIVITY_OPPORTUNITY: "Custom",
        LCMessageType.TYPE_LIVE_CHAT: "Live_Chat",
        LCMessageType.TYPE_ACTIVITY_APPOINTMENT: "Custom",
}


def get_message_channel(message_type: LCMessageType) -> str:
    message_channel = message_type_mapping.get(message_type)
    if message_channel is None:
        logger.error(f"Invalid message type {message_type}")
        return None
    return message_channel


class LCMessageStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    UNDELIVERED = "undelivered"
    CONNECTED = "connected"
    FAILED = "failed"
    OPENED = "opened"


class LCMessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class LCMessage(BaseModel):
    id: str
    direction: Optional[LCMessageDirection] = None
    status: Optional[LCMessageStatus] = None
    type: LCMessageType
    attachments: Optional[List[HttpUrl]] = []
    body: str = ""
    contentType: str = ""
    dateAdded: datetime
    userId: Optional[str] = None
    source: Optional[str] = None

    def model_dump(self, **kwargs):
        # Convert the datetime to a string
        data = super().model_dump()
        data["dateAdded"] = self.dateAdded.isoformat()
        data["attachments"] = [str(url) if url else None for url in self.attachments]
        return data


class LeadConnectorConfig(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str
    scope: list[str]
    user_type: str
    company_id: str
    location_id: str
    user_id: str
    token_expiry: datetime = None  # To track token expiry time


class DNDSettings(BaseModel):
    status: str
    message: str
    code: str


class AttributionSource(BaseModel):
    url: Optional[str] = None
    campaign: Optional[str] = None
    utmSource: Optional[str] = None
    utmMedium: Optional[str] = None
    utmContent: Optional[str] = None
    referrer: Optional[str] = None
    campaignId: Optional[str] = None
    fbclid: Optional[str] = None
    gclid: Optional[str] = None
    msclikid: Optional[str] = None
    dclid: Optional[str] = None
    fbc: Optional[str] = None
    fbp: Optional[str] = None
    fbEventId: Optional[str] = None
    userAgent: Optional[str] = None
    ip: Optional[str] = None
    medium: Optional[str] = None
    mediumId: Optional[str] = None


class CustomField(BaseModel):
    id: str
    value: str


class LCContactInfo(BaseModel):
    id: str
    name: Optional[str] = None
    locationId: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[EmailStr] = None
    emailLowerCase: Optional[EmailStr] = None
    timezone: Optional[str] = None
    companyName: Optional[str] = None
    phone: Optional[str] = None
    dnd: Optional[bool] = None
    dndSettings: Optional[Dict[str, DNDSettings]] = None
    type: Optional[str] = None
    source: Optional[str] = None
    assignedTo: Optional[str] = None
    address1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postalCode: Optional[str] = None
    website: Optional[HttpUrl] = None
    tags: Optional[List[str]] = None
    dateOfBirth: Optional[str] = None
    dateAdded: Optional[str] = None
    dateUpdated: Optional[str] = None
    attachments: Optional[List[str]] = None
    ssn: Optional[str] = None
    gender: Optional[str] = None
    keyword: Optional[str] = None
    firstNameLowerCase: Optional[str] = None
    fullNameLowerCase: Optional[str] = None
    lastNameLowerCase: Optional[str] = None
    lastActivity: Optional[str] = None
    customFields: Optional[List[CustomField]] = None
    businessId: Optional[str] = None
    attributionSource: Optional[AttributionSource] = None
    lastAttributionSource: Optional[AttributionSource] = None
    additionalEmails: Optional[List[str]] = None
    additionalPhones: Optional[List[str]] = None

class ContactResponse(BaseModel):
    contact: LCContactInfo

NOT_SUPPORTED_MESSAGE_TYPES = [LCMessageType.TYPE_CALL, LCMessageType.TYPE_EMAIL]

def convert_response_to_leadconnector_config(
    response_data: dict,
) -> LeadConnectorConfig:
    """
    Converts the response data from LeadConnector API to a LeadConnectorConfig object.

    Args:
        response_data (dict): The response data from the LeadConnector API.

    Returns:
        LeadConnectorConfig: The converted LeadConnectorConfig object.

    """
    return LeadConnectorConfig(
        user_id=response_data["userId"],
        company_id=response_data["companyId"],
        location_id=response_data["locationId"],
        scope=str(response_data["scope"]).split(" "),
        token_type=response_data["token_type"],
        access_token=response_data["access_token"],
        refresh_token=response_data["refresh_token"],
        expires_in=response_data["expires_in"],
        user_type=response_data["userType"],
    )


def log_leadconnector_config(config: LeadConnectorConfig) -> None:
    """
    Logs the LeadConnectorConfig object after preparing it for logging.

    Args:
        config (LeadConnectorConfig): The LeadConnectorConfig object to be logged.

    Returns:
        None
    """
    # prepare the config to be logged and log it
    printable_response = config.model_copy()
    printable_response.access_token = (
        config.access_token[:4] + "..." + config.access_token[-4:]
    )
    printable_response.refresh_token = (
        config.refresh_token[:4] + "..." + config.refresh_token[-4:]
    )
    response_data_beautify = printable_response.model_dump()
    response_data_beautify = json.dumps(response_data_beautify, indent=4)
    logger.info(response_data_beautify)


def save_leadconnector_config(config: LeadConnectorConfig, file_path: str) -> None:
    """
    Saves the LeadConnectorConfig object to a file.

    Args:
        config (LeadConnectorConfig): The LeadConnectorConfig object to be saved.
        file_path (str, optional): The file path to save the LeadConnectorConfig object. Defaults to ".config/leadconnector_config.json".

    Returns:
        None
    """
    with open(file_path, "w", encoding="utf-8") as file:
        data = config.model_dump()
        json.dump(data, file, indent=4)


async def get_and_save_token(
    code: str, state: str, file_path=".config/leadconnector_config.json"
):
    """
    Retrieves an access token using the provided authorization code and saves it to a file.

    Args:
        code (str): The authorization code.
        state (str): The login state.
        file_path (str, optional): The file path to save the access token. Defaults to ".config/leadconnector_config.json".

    Raises:
        httpx.HTTPError: If failed to get the access token.

    Returns:
        None
    """
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    logger.info(f"login state received: {state}")
    async with AsyncClient() as client:
        logger.info(f"requesting access token from: {TOKEN_URL}")
        response = await client.post(TOKEN_URL, data=data)
        logger.info(f"{TOKEN_URL} response status code: {response.status_code}")
    if response.status_code != 200:
        raise httpx.HTTPError(f"Failed to get access token: {response.text}")
    response_data = response.json()

    response = convert_response_to_leadconnector_config(response_data)
    log_leadconnector_config(response)
    save_leadconnector_config(response, file_path)


# get the configurations from the config file
def get_leadconnector_config_file(file_path) -> LeadConnectorConfig:
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
        # Calculate and set the token expiry time
        data["token_expiry"] = datetime.now() + timedelta(seconds=data["expires_in"])
        config = LeadConnectorConfig(**data)
    return config


def get_auth_url(scope=None, state="6969"):
    # f"{self.auth_url}?response_type=code&client_id={self.client_id}&redirect_uri={self.redirect_uri}&scope={self.scope}&state={state}"

    if scope is None:
        scope = SCOPE
    scope = "%20".join(scope.split())
    url = f"{AUTHORIZATION_URL}?"
    url += "response_type=code"
    url += f"&client_id={CLIENT_ID}"
    url += f"&redirect_uri={REDIRECT_URI}"
    url += f"&scope={scope}"
    url += f"&state={state}"

    return url


def filter_messages_by_type(
    messages: List[LCMessage], allowed_types: List[LCMessageType]
) -> List[LCMessage]:
    return [msg for msg in messages if msg.type in allowed_types]


from llama_index.core.base.llms.types import ChatMessage, MessageRole


def convert_lcmessage_to_chatmessage(messages: List[LCMessage]) -> List[ChatMessage]:

    filtered_messages = [
        msg
        for msg in messages
        if msg.status
        not in {
            LCMessageStatus.SCHEDULED,
            LCMessageStatus.UNDELIVERED,
            LCMessageStatus.FAILED,
        }
    ]

    chat_messages = []
    for msg in filtered_messages:
        role = (
            MessageRole.ASSISTANT
            if msg.direction == LCMessageDirection.OUTBOUND
            else MessageRole.USER
        )
        chat_message = ChatMessage(
            role=role, content=msg.body, additional_kwargs={"dateAdded": str(msg.dateAdded)}
        )
        chat_messages.append(chat_message)

    return chat_messages


def is_ava_permitted_to_engage(contact_info: LCContactInfo) -> bool:

    if not isinstance(contact_info, LCContactInfo):
        raise ValueError("contact_info must be an instance of LCContactInfo")

    if PERMISSION_TAG not in contact_info.tags:
        logger.info(
            f"Contact {contact_info.id} does not have the permission tag '{PERMISSION_TAG}', cannot engage with the contact"
        )
        return False

    return True


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


# Example usage:
# connector = LeadConnector()
# response = connector.make_request("GET", "https://api.example.com/your_endpoint")
# print(response.json())
