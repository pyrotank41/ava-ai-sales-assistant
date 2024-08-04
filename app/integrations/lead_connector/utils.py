from datetime import datetime, timedelta
import json
import os
from typing import List, Optional
from httpx import AsyncClient
import httpx
from loguru import logger
from integrations.lead_connector.config import AUTHORIZATION_URL, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, TOKEN_URL
from integrations.lead_connector.models import LCMessage, LCMessageDirection, LCMessageStatus, LCMessageType, LeadConnectorConfig
from datamodel import ChatMessage, MessageRole

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
def get_scope():
    return SCOPE

message_type_mapping = (
    {  # the mapping of the message type required when sending a message
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
)


def get_message_channel(message_type: LCMessageType) -> str:
    message_channel = message_type_mapping.get(message_type)
    if message_channel is None:
        logger.error(f"Invalid message type {message_type}")
        return None
    return message_channel


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


# def save_leadconnector_config(config: LeadConnectorConfig, file_path: str) -> None:
#     """
#     Saves the LeadConnectorConfig object to a file.

#     Args:
#         config (LeadConnectorConfig): The LeadConnectorConfig object to be saved.
#         file_path (str, optional): The file path to save the LeadConnectorConfig object. Defaults to ".config/leadconnector_config.json".

#     Returns:
#         None
#     """

#     # file_path=".config/leadconnector_config.json",
#     file_path = file_path
#     os.makedirs(os.path.dirname(file_path), exist_ok=True)
#     file_name = "leadconnector_config.json"
#     file_path = os.path.join(file_path, file_name)

#     # lets make sure the directory exists if not create it
#     os.makedirs(os.path.dirname(file_path), exist_ok=True)

#     with open(file_path, "w", encoding="utf-8") as file:
#         data = config.model_dump()
#         json.dump(data, file, indent=4)
        
def save_leadconnector_config(
    config: LeadConnectorConfig, file_path: Optional[str] = None
) -> None:
    """
    Saves the LeadConnectorConfig object to a file.

    Args:
        config (LeadConnectorConfig): The LeadConnectorConfig object to be saved.
        file_path (str, optional): The directory path to save the LeadConnectorConfig object.
                                   If not provided, defaults to ".config".

    Returns:
        None
    """
    if file_path is None:
        file_path = ".config"


    if not os.path.exists(file_path):
        os.makedirs(file_path, exist_ok=True)
        logger.info(f"Directory created: {file_path}")

    file_name = "leadconnector_config.json"
    full_file_path = os.path.join(file_path, file_name)

    try:
        with open(full_file_path, "w", encoding="utf-8") as file:
            data = config.model_dump()
            json.dump(data, file, indent=4)
    except Exception as e:
        raise Exception(f"Error saving config to {full_file_path}: {str(e)}") from e


async def get_and_save_token(
    code: str,
    state: str,
    file_path=".config",
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
    redirect_url = REDIRECT_URI
    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET
    token_url = TOKEN_URL

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_url,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    logger.info(f"login state received: {state}")
    async with AsyncClient() as client:
        logger.info(f"requesting access token from: {token_url}")
        response = await client.post(token_url, data=data)
        logger.info(f"{token_url} response status code: {response.status_code}")
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


def get_auth_url(
        scope=None,
        state="6969"
    ):
    # f"{self.auth_url}?response_type=code&client_id={self.client_id}&redirect_uri={self.redirect_uri}&scope={self.scope}&state={state}"
    auth_url = AUTHORIZATION_URL
    client_id = CLIENT_ID
    redirect_uri = REDIRECT_URI
    if scope is None:
        scope = get_scope()
    scope = "%20".join(scope.split())
    url = f"{auth_url}?"
    url += "response_type=code"
    url += f"&client_id={client_id}"
    url += f"&redirect_uri={redirect_uri}"
    url += f"&scope={scope}"
    url += f"&state={state}"

    return url


def filter_messages_by_type(
    messages: List[LCMessage], allowed_types: List[LCMessageType]
) -> List[LCMessage]:
    return [msg for msg in messages if msg.type in allowed_types]


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
            role=role,
            content=msg.body,
            additional_kwargs={"dateAdded": str(msg.dateAdded)},
        )
        chat_messages.append(chat_message)

    return chat_messages
