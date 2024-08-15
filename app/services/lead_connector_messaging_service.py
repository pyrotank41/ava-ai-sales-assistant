import json
from typing import List, Optional
from loguru import logger

from integrations.lead_connector.leadconnector import (
    NOT_SUPPORTED_MESSAGE_TYPES,
    LeadConnector,
    NoConversationFoundError,
)

from integrations.lead_connector.models import LCContactInfo, LCMessage, LCMessageType
from integrations.lead_connector.utils import (
    convert_lcmessage_to_chatmessage,
    filter_messages_by_type,
    get_message_channel,
)
from services.ava_service import AvaService, ContactInfo
from services.base_message_service import MessagingService

from config import (
    AGENT_ENGAGED_TAG,
    AVA_INTERACTED_TAG,
    GHL_CUSTOM_FIELD_LEAD_STATE_KEY,
    GHL_CUSTOM_FIELD_NUMBER_OF_INTERACTION_KEY,
    MAX_CONVERSATION_COUNT,
    AVA_MAX_SMS_CONVO_REACHED,
    PERMISSION_TAG,
)


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
        if AGENT_ENGAGED_TAG in contact_info.tags:
            logger.info(
                f"Contact {contact_info.id} has the permission tag '{PERMISSION_TAG}', but the contact has been engaged by an agent, cannot engage with the contact"
            )

        return True

    def get_conversation_id(self, contact_id: str):
        try:
            conversation_id = self.lc.get_conversation_id(contact_id=contact_id)
        except NoConversationFoundError as e:
            logger.warning(f"NoConversationFoundError: {e}")
            conversation_id = self.lc.create_conversation(contact_id=contact_id).get(
                "id"
            )
        except Exception as e:
            raise e

        return conversation_id

    def get_all_messages_from_conversation(
        self, conversation_id: str
    ) -> List[LCMessage]:

        lc_messages = self.lc.get_all_messages(conversation_id)
        return lc_messages

    def get_latest_message_type(
        self, lc_messages: List[LCMessage]
    ) -> Optional[LCMessageType]:
        if len(lc_messages) == 0:
            return None

        recent_message = lc_messages[-1]
        message_type = LCMessageType(recent_message.messageType)
        return message_type

    def get_all_messages(
        self,
        contact_id: str,
    ) -> List[LCMessage]:

        conversation_id = self.get_conversation_id(contact_id)
        return self.get_all_messages_from_conversation(conversation_id=conversation_id)

    def get_custom_field_value(
        self, contact_info: LCContactInfo, field_key: str
    ) -> str:
        # from contact_info get the custom field value using the field_key and custom_fields_map
        field_id = self.get_custom_field_id(field_key)
        customFields = contact_info.customFields
        for field in customFields:
            if field.id == field_id:
                return field.value

    def get_custom_field_id(self, field_key: str) -> str:
        return self.custom_fields_map.get(field_key)

    def convert_lc_contact_info_to_contact_info(
        self, contact_info: LCContactInfo
    ) -> ContactInfo:
        return ContactInfo(
            id=contact_info.id,
            full_name=f"{contact_info.firstName} {contact_info.lastName}",
            first_name=contact_info.firstName,
            last_name=contact_info.lastName,
            address=contact_info.address1,
            city=contact_info.city,
            state=contact_info.state,
            timezone=contact_info.timezone,
            lead_state=self.get_custom_field_value(contact_info, "contact.lead_state"),
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
                ),
            },
        )

    def engage_with_contact(
        self, contact_id: str, message_type: LCMessageType = LCMessageType.TYPE_SMS
    ):

        # validations ----------------
        if contact_id is None:
            raise ValueError("contact_id must be provided")

        # Check if ava is allowed to engage with the contact ---------------------------------
        lc_contact_info = self.lc.get_contact_info(contact_id)

        if not self._is_ava_permitted_to_engage(lc_contact_info):
            return
        # Ava is allowed to engage with the contact, lets engage with the contact ----------------
        # get all the messages from the contact
        lc_messages = self.get_all_messages(contact_id=contact_id)
        # engage ava with the contact
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
        # validations ----------------
        if contact_id is None:
            raise ValueError("contact_id must be provided")

        if conversation_id is None:
            conversation_id = self.get_conversation_id(contact_id)

        lc_contact_info = self.lc.get_contact_info(contact_id)
        logger.debug(
            json.dumps(lc_contact_info.model_dump(exclude_none=True), indent=4)
        )

        # Check if ava is allowed to engage with the contact ---------------------------------
        # Check 1: lets make sure if ava is allowed to engage with the contact
        if not self._is_ava_permitted_to_engage(lc_contact_info):
            return

        # Check 2: lets check if the conversation count is less than MAX_CONVERSATION_COUNT
        if self.get_number_of_interactions(lc_contact_info) >= MAX_CONVERSATION_COUNT:

            # check if the user has been notified in the past about the conversation limit
            if AVA_MAX_SMS_CONVO_REACHED in lc_contact_info.tags:
                logger.info(
                    f"MAX conversation limit reached for the contact {lc_contact_info.name},and the User has been notified in the past"
                )
                return
            # notify the user about the conversation limit, as the user has not been notified in the past
            self.notify_users(
                f"Conversation limit reached for contact {lc_contact_info.name}\n{lc_contact_info.phone}\n{lc_contact_info.email}, please interact with the contact or reset the conter"
            )

            # add the tag to the contact so we do not notify the user again
            self.lc.add_tag_to_contact(
                contact_id=contact_id, tag=AVA_MAX_SMS_CONVO_REACHED
            )

            # return as we do not want to engage with the contact
            return
        # Ava is allowed to engage with the contact, lets engage with the contact ----------------

        # step 1: lets get all the messages from the conversation
        lc_messages = self.get_all_messages_from_conversation(
            conversation_id=conversation_id
        )
        message_type = self.get_latest_message_type(lc_messages)
        logger.debug(f"Message type: {message_type}")
        if message_type is None:
            logger.warning(
                f"There must be a mistake here, no messages found for contact {contact_id} to engage with ava, did you mean to use engage_with_contact to start the conversation?"
            )
            return

        # stpe 2: lets engage ava with the contact
        self.engage_ava(
            contact_id=contact_id,
            lc_messages=lc_messages,
            lc_contact_info=lc_contact_info,
            message_type=message_type,
        )

    def engage_ava(
        self,
        contact_id: str,
        lc_messages: List[LCMessage],
        lc_contact_info: LCContactInfo,
        message_type: LCMessageType,
    ):

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

        resp = ava_service.respond(
            conversation_messages=chat_messages,
            contact_info=self.convert_lc_contact_info_to_contact_info(lc_contact_info),
        )
        generation_state = resp.is_generated
        message = resp.content
        lead_state = resp.lead_state

        if generation_state is True:

            # dividing messages by new line se we send them as seperate messages
            message_split = message.split("\n\n")
            for message in message_split:
                self.lc.send_message(
                    contact_id=contact_id,
                    message=message,
                    message_channel=get_message_channel(message_type),
                )

            # adding ava_interacted tag to the contact
            self.add_ava_interacted_tag(lc_contact_info)

            # increment the message count for the conact
            self.increment_message_counter(lc_contact_info)

            # update the lead state
            if lead_state is not None:
                self.lc.updated_contact_custom_field_value(
                    contact_id=lc_contact_info.id,
                    custom_field_id=self.get_custom_field_id(
                        GHL_CUSTOM_FIELD_LEAD_STATE_KEY
                    ),
                    value=lead_state,
                )

        else:  # notify the contact owner and add a task to the contact_id
            self.notify_users(message)

    def get_number_of_interactions(self, contact_info: LCContactInfo):
        custom_field_id = self.get_custom_field_id(
            GHL_CUSTOM_FIELD_NUMBER_OF_INTERACTION_KEY
        )
        if custom_field_id is not None:
            # get the current value of the custom field
            current_value = self.get_custom_field_value(
                contact_info, GHL_CUSTOM_FIELD_NUMBER_OF_INTERACTION_KEY
            )

            try:
                current_value = int(current_value)
            except TypeError:
                current_value = 0
                self.lc.updated_contact_custom_field_value(
                    contact_id=contact_info.id,
                    custom_field_id=custom_field_id,
                    value=str(current_value),
                )

            return current_value

        raise ValueError("Custom field 'contact.number_of_interactions' not found")

    def increment_message_counter(self, contact_info: LCContactInfo):
        """
        Increments the message counter for a given contact.

        this helps us keep track of the number of interactions ava had with the contact

        Args:
            contact_info (LCContactInfo): The contact information.
        Returns:
            LCContactInfo: The updated contact information with the incremented message counter.
        """
        custom_field_id = self.get_custom_field_id(
            GHL_CUSTOM_FIELD_NUMBER_OF_INTERACTION_KEY
        )
        if custom_field_id is not None:
            # get the current value of the custom field
            current_value = self.get_custom_field_value(
                contact_info, GHL_CUSTOM_FIELD_NUMBER_OF_INTERACTION_KEY
            )

            try:
                current_value = int(current_value)
            except ValueError:
                current_value = 0
            except TypeError:
                current_value = 0

            current_value += 1

            logger.info(f"incrementing custom field value: {current_value}")

            # update the custom field
            resp = self.lc.updated_contact_custom_field_value(
                contact_id=contact_info.id,
                custom_field_id=custom_field_id,
                value=str(current_value),
            )
            updated_lc_contact_info = LCContactInfo(**resp)
            logger.debug(
                f"incremented custom field value: {updated_lc_contact_info.customFields}"
            )
            return updated_lc_contact_info

    def add_ava_interacted_tag(self, contact_info: LCContactInfo):
        """Function to add the tag ava_interacted to the contact.

        This function helps us track the contacts that have interacted with ava.

        Args:
            contact_info (LCContactInfo): The contact information.

        Returns:
            None
        """
        """function to add the tag ava_interacted to the contact, this helps us with tracking the contacts that have interacted with ava"""
        # adding the tag to the contact
        if "ava_interacted" not in contact_info.tags:
            self.lc.add_tag_to_contact(
                contact_id=contact_info.id, tag=AVA_INTERACTED_TAG
            )
            logger.debug(f"Added tag {AVA_INTERACTED_TAG} to contact {contact_info.id}")
            return
        logger.debug(
            f"Tag {AVA_INTERACTED_TAG} already exists for contact {contact_info.id}, skipping this operation"
        )

    def notify_users(self, message: str):
        # notify_users = self.lc.get_user_by_location()
        # makes sure the users have a contact created with their email and phone number in ghl
        # for now we are hardcoding thie user ids to notify the users for testing
        notify_users_contact_id = ["n66TIjUfMUrSQCZzypK6"]
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

    # messaging_service.process_to_inbound_message("26cs4MUPgfX8x6NcVZ61")

    # testing the increment message counter
    contact_id = "mmprUyomgvUt0m3R5PLu"
    lc_contact_info = messaging_service.lc.get_contact_info(contact_id)
    # messaging_service.increment_message_counter(lc_contact_info)

    # testing get number of interactions
    # print(messaging_service.get_number_of_interactions(lc_contact_info))

    # testing add_ava_interacted_tag
    print(messaging_service.add_ava_interacted_tag(lc_contact_info))
