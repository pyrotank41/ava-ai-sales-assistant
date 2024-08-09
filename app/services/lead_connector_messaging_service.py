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

from integrations.lead_connector.models import LCContactInfo, LCMessage, LCMessageType
from integrations.lead_connector.utils import (
    convert_lcmessage_to_chatmessage,
    filter_messages_by_type,
    get_message_channel,
)
from datamodel import ChatMessage
from services.ava_service import AvaService, ContactInfo
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

        # getting the custom fields for the location
        self.custom_fields = self.lc.get_custom_fields()
        self.custom_fields_map = self.lc.get_custom_fields_id_key_mapping()

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

    def get_all_messages_from_conversation(
        self, contact_id: str, conversation_id: Optional[str] = None
    ):  
        # TODO: seperation of concern, this method gets all the conversations and also get the latest message type, seperat it.
        if conversation_id is None:
            conversation_id = self.lc.get_conversation_id(contact_id=contact_id)
        lc_messages = self.lc.get_all_messages(conversation_id)
        recent_message = lc_messages[-1]
        message_type = LCMessageType(recent_message.type)
        return lc_messages, message_type

    def get_custom_field_value(self, contact_info: LCContactInfo, field_key:str)->str:
        # from contact_info get the custom field value using the field_key and custom_fields_map
        field_id = self.custom_fields_map.get(field_key)
        customFields = contact_info.customFields
        for field in customFields:
            if field.id == field_id:
                return field.value

    def convert_lc_contact_info_to_contact_info(self, contact_info: LCContactInfo)->ContactInfo:
        return ContactInfo(
                id=contact_info.id,
                full_name=f"{contact_info.firstName} {contact_info.lastName}",
                first_name=contact_info.firstName,
                last_name=contact_info.lastName,
                address=contact_info.address1,
                city=contact_info.city,
                state=contact_info.state,
                timezone=contact_info.timezone,
                lead_state=self.get_custom_field_value(
                    contact_info, "contact.lead_state"
                ),
                pre_qualification_qa={
                    "roof_age": self.get_custom_field_value(
                        contact_info, "contact.how_old_is_your_roof"
                    ),
                    "credit_score": self.get_custom_field_value(
                        contact_info, "contact.is_your_credit_more_than_640"
                    ),
                    "average_monthly_electric_bill": self.get_custom_field_value(
                        contact_info, "contact.what_is_your_average_electricity_bill"
                    ),
                    "annual_household_income": self.get_custom_field_value(
                        contact_info, "contact.household_income"
                    ),
                    "homeowner": self.get_custom_field_value(
                        contact_info, "contact.are_your_a_homeowner"
                    )
                    
                }
        )

    def engage_with_contact(self, contact_id: str, message_type: LCMessageType = LCMessageType.TYPE_SMS):
        
        lc_contact_info = self.lc.get_contact_info(contact_id)
        if not self._is_ava_permitted_to_engage(lc_contact_info):
            return
        conversation_id = self.lc.get_conversation_id(contact_id)

        lc_messages, _ = self.get_all_messages_from_conversation(
            contact_id=contact_id, conversation_id=conversation_id
        )

        self.engage_ava(
            contact_id=contact_id,
            lc_messages=lc_messages,
            lc_contact_info=lc_contact_info,
            message_type=message_type,
        )


    def process_to_inbound_message(
        self,
        contact_id: str,
        conversation_id: Optional[str] = None,
    ):

        lc_contact_info = self.lc.get_contact_info(contact_id)
        logger.debug(json.dumps(lc_contact_info.model_dump(exclude_none=True), indent=4))

        # lets make sure if ava is allowed to engage with the contact
        if not self._is_ava_permitted_to_engage(lc_contact_info):
            return

        # step 1: lets get all the messages from the conversation
        lc_messages, message_type = self.get_all_messages_from_conversation(
            contact_id=contact_id, conversation_id=conversation_id
        )

        self.engage_ava(
            contact_id=contact_id,
            lc_messages=lc_messages,
            lc_contact_info=lc_contact_info,
            message_type=message_type,
        )

    def engage_ava(self, 
                   contact_id: str,
                   lc_messages: List[LCMessage],
                   lc_contact_info: LCContactInfo,
                   message_type: LCMessageType):

        # making sure the message type is supported
        if message_type in NOT_SUPPORTED_MESSAGE_TYPES:
            logger.warning(
                f"Recieved message type {message_type}, it is currently not supported, not engaging with ava"
            )
            return

        # Step 2: filtering message by type se we do not crosscontiminate the messages from different channels
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
        ava_service = AvaService()

        generation_state, message = ava_service.respond(
            conversation_messages=chat_messages,
            contact_info=self.convert_lc_contact_info_to_contact_info(lc_contact_info),
        )

        if generation_state is True:
            # dividing messages by new line se we send them as seperate messages
            message_split = message.split("\n\n")
            for message in message_split:
                self.lc.send_message(
                    contact_id=contact_id,
                    message=message,
                    message_channel=get_message_channel(message_type),
                )

        else:  # notify the contact owner and add a task to the contact_id
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
    # lc_contact_info = messaging_service.lc.get_contact_info("6ygr3QkYGJfEGfNJ2FvD")
    # contact_info = messaging_service.convert_lc_contact_info_to_contact_info(lc_contact_info)
    # logger.info(json.dumps(contact_info.dict(), indent=4))
    # logger.info(messaging_service.notify_users("This is a test notification message"))

    messaging_service.process_to_inbound_message(
        "zV4uZksd5T66HTqnH6Td"
    )
