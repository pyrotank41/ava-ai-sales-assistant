import json
import os
import sys
from typing import List, Optional

from loguru import logger

# # path to the root dir
# path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
# logger.debug(f"Adding path to system path: {path}")
# sys.path.append(path)

from config import PERMISSION_TAG
from integrations.lead_connector.leadconnector import (
    NOT_SUPPORTED_MESSAGE_TYPES,
    LeadConnector,
)

from integrations.lead_connector.models import LCContactInfo, LCMessageType
from integrations.lead_connector.utils import (
    convert_lcmessage_to_chatmessage,
    filter_messages_by_type,
    get_message_channel,
)
from datamodel import ChatMessage
from services.ava_service import AvaService
from services.base_message_service import MessagingService


class LeadConnectorMessageingService(MessagingService):
    def __init__(
        self,
        lead_connector: Optional[LeadConnector] = None,
        location_id: Optional[str] = None,
    ):
        self.lc = lead_connector
        if lead_connector is None and location_id is not None:
            self.lc = LeadConnector(location_id=location_id)
        elif lead_connector is None and location_id is None:
            raise ValueError("Either lead_connector or location_id must be provided")

    def process_special_codes(self, message: str, conversation_id: str) -> bool:
        RESET_CONVERSATION_CODE = "*RESET#"
        if message == RESET_CONVERSATION_CODE:
            logger.info(f"Resetting conversation {conversation_id}")
            self.lc.delete_conversation(conversation_id)
            return True

    def _is_ava_permitted_to_engage(self, contact_info: LCContactInfo) -> bool:

        if not isinstance(contact_info, LCContactInfo):
            raise ValueError("contact_info must be an instance of LCContactInfo")

        if PERMISSION_TAG not in contact_info.tags:
            logger.info(
                f"Contact {contact_info.id} does not have the permission tag '{PERMISSION_TAG}', cannot engage with the contact"
            )
            return False

        return True

    def respond_to_inbound_message(self,
                                   contact_id: str,
                                   user_message: Optional[str] = None,
                                   conversation_id: Optional[str] = None):

        # step 1: lets make sure if ava is allowed to engage with the contact
        contact_info = self.lc.get_contact_info(contact_id)
        logger.debug(json.dumps(contact_info.model_dump(exclude_none=True), indent=4))
        if not self._is_ava_permitted_to_engage(contact_info):
            return

        # step 2: lets get all the messages from the conversation
        if conversation_id is None:
            conversation_id = self.lc.get_conversation_id(
                    contact_id=contact_id
                )
        lc_messages = self.lc.get_all_messages(conversation_id)
        recent_message = lc_messages[-1]

        # step 2.1: lets get the message type, so we can filter the messages
        # based on the source of message
        message_type = LCMessageType(recent_message.type)

        # making sure the message type is supported
        if message_type in NOT_SUPPORTED_MESSAGE_TYPES:
            logger.warning(
                f"Recieved message type {message_type}, it is currently not supported, skipping this webhook event"
            )
            return

        # filtering message by type se we do not crosscontiminate the messages from different channels
        filtered_lc_messages = filter_messages_by_type(
            messages=lc_messages, allowed_types=[message_type]
        )

        # converting the messages to ChatMessage, So it works with ava
        chat_messages = convert_lcmessage_to_chatmessage(filtered_lc_messages)
        logger.debug(f"Converted {len(chat_messages)} messages")
        logger.debug(
            json.dumps([message.dict() for message in chat_messages], indent=4)
        )

        # validating the chat_messages, only list is allowed
        if not isinstance(chat_messages, List):
            raise ValueError("chat_messages should be a list")
        if not all(isinstance(message, ChatMessage) for message in chat_messages):
            raise ValueError("chat_messages should be a list of ChatMessage")

        # lets send the message to ava to generate a response

        ava_service = AvaService()
        chat_history = chat_messages[0:-1]

        if user_message is not None: # validating if user message is the last message, if not, ava is reaching out further.
            conversation_user_message = chat_messages[-1]
            if conversation_user_message.content != user_message:
                raise ValueError("User message should be the last message in the conversation")

            ava_service_resp = ava_service.generate_message( # this call will generate a response to the user message
                user_message=user_message,
                chat_history=chat_history,
                contact_info=contact_info.model_dump(exclude_unset=True)
            )
        else:
            ava_service_resp = ava_service.generate_message(  # this call will generate a response to re-engage the lead
                chat_history=chat_history, contact_info=contact_info
            )
        generation_state, message = ava_service_resp

        if generation_state is True:
            # dividing messages by new line se we send them as seperate messages
            message_split = message.split("\n\n")
            for message in message_split:
                self.lc.send_message(
                    contact_id=contact_id,
                    message=message,
                    message_channel=get_message_channel(message_type),
                )
        else: # notify the contact owner and add a task to the contact_id
            self.notify_users(message)

    def notify_users(self, message: str):
        # notify_users = self.lc.get_user_by_location()
        # makes sure the users have a contact created with their email and phone number in ghl
        # for now we are hardcoding thie user ids to notify the users for testing
        notify_users_contact_id = ["6smJfQjKMu95Y58rIcYl", "n66TIjUfMUrSQCZzypK6"]
        contact_infos: List[LCContactInfo] = []
 
        for contact_id in notify_users_contact_id:
            try:
                contact_info = self.lc.get_contact_info(contact_id)
            except Exception as e:
                logger.error(f"Error fetching contact info for {contact_id}: {e}")
                continue
            contact_infos.append(contact_info)

        for contact in contact_infos:
            try:
                self.lc.send_message(
                    contact_id=contact.id,
                    message=message,
                    message_channel="SMS",
                )
            except Exception as e:
                logger.error(f"Error sending message to {contact.id}: {e}")
                continue

if __name__ == "__main__":
    lc = LeadConnector(location_id="hqDwtNvswsupf6BT1Qxt")
    messaging_service = LeadConnectorMessageingService(lc)
    # contact_id = "6smJfQjKMu95Y58rIcYl"
    # conversation_id = lc.get_conversation_id(contact_id=contact_id)
    # lc_message = lc.get_all_messages(conversation_id)
    # recent_message = lc_message[-1]
    # message_type = LCMessageType(recent_message.type)
    # logger.debug(f"Message type: {message_type}")
    # logger.debug(json.dumps(lc_message, indent=4))
    # logger.debug(f"conversation_id: {conversation_id}")
    # logger.debug(f"contact_id: {contact_id}")
    # logger.debug(json.dumps(lc.get_contact_info(contact_id).model_dump(exclude_none=True), indent=4))
    # logger.debug(json.dumps(lc.get_user_by_location(), indent=4))
    logger.info(messaging_service.notify_users("This is a test notification message"))
