import json
from typing import List, Optional

from loguru import logger
from app.ava.ava import Ava
from app.integrations.leadconnector import NOT_SUPPORTED_MESSAGE_TYPES, LCMessageType, LeadConnector, convert_lcmessage_to_chatmessage, filter_messages_by_type, get_message_channel, is_ava_permitted_to_engage


class LeadConnectorMessageingService():
    def __init__(
            self, 
            lead_connector: Optional[LeadConnector] = None,
            ava: Optional[Ava]=None
        ):
        self.ava = ava
        self.lead_connector = lead_connector

        if ava is None:
            self.ava = Ava()
        if lead_connector is None:
            self.lc = LeadConnector()

    def process_special_codes(self, message:str, conversation_id:str)-> bool:
        RESET_CONVERSATION_CODE = "*RESET#"
        if message == RESET_CONVERSATION_CODE:
            logger.info(f"Resetting conversation {conversation_id}")
            self.lc.delete_conversation(conversation_id)
            return True

    def respond(self, contact_id: str, conversation_id: str):
        
        # step 1: lets make sure if ava is allowed to engage with the contact
        contact_info = self.lc.get_contact_info(contact_id)
        logger.debug(json.dumps(contact_info.model_dump(exclude_none=True), indent=4))
        if not is_ava_permitted_to_engage(contact_info):
            return

        # step 2: lets get all the messages from the conversation
        lc_messages = self.lc.get_all_messages(conversation_id)
        recent_message = lc_messages[-1]

        # step 2.1: lets get the message type, so we can filter the messages based on the source of message
        message_type = LCMessageType(recent_message.type)

        # make sure we only get the messages_type we support
        if message_type in NOT_SUPPORTED_MESSAGE_TYPES:
            logger.warning(
                f"Recieved message type {message_type}, it is currently not supported, skipping this webhook event"
            )
            return None

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

        # lets send the message to ava to generate a response
        if not isinstance(chat_messages, List):
            raise ValueError("chat_messages should be a list")

        ava = Ava()
        chat_history = chat_messages[0:-1]
        user_message = chat_messages[-1]
        ava_message = ava.chat(user_message, chat_history)

        message_split = ava_message.message.content.split("\n\n")

        for message in message_split:
            self.lc.send_message(
                contact_id=contact_id,
                message=message,
                message_channel=get_message_channel(message_type),
            )
