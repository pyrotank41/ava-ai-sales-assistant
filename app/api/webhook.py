from datetime import datetime
import json
from typing import List
from fastapi import APIRouter, Request, BackgroundTasks
from loguru import logger
from pydantic import BaseModel, Field

from app.ava.ava import Ava
from app.integrations.leadconnector import (
    LCMessageType,
    LeadConnector,
    convert_lcmessage_to_chatmessage,
    filter_messages_by_type,
)

with open(".config/accepted_locations.json", "r") as file:
    file_data = json.load(file)
    accepted_locations = file_data["locations"]


class LeadConnectorWHTypeInboundMessage(BaseModel):
    type: str = Field(..., example="InboundMessage")
    locationId: str = Field(..., example="l1C08ntBrFjLS0elLIYU")
    attachments: List[str] = Field(..., example=[])
    body: str = Field(..., example="This is a test message")
    contactId: str = Field(..., example="cI08i1Bls3iTB9bKgFJh")
    contentType: str = Field(..., example="text/plain")
    conversationId: str = Field(..., example="fcanlLgpbQgQhderivVs")
    dateAdded: datetime = Field(..., example="2021-04-21T11:31:45.750Z")
    direction: str = Field(..., example="inbound")
    messageType: str = Field(..., example="SMS")
    status: str = Field(..., example="delivered")


router = APIRouter()


@router.post("/leadconnector")
async def leadconnector(request: Request):
    request = await request.json()

    if request["locationId"] not in accepted_locations:
        logger.debug(f"Location {request['locationId']} not accepted")
        return {"status": "rejected"}
    else:
        logger.debug(
            f"Location {request['locationId'][:4]}****{request['locationId'][-4:]} accepted"
        )

    request_type = request["type"]
    logger.info(f"Leadconnector webhook type {request_type} recieved")

    if request_type == "ContactTagUpdate":
        logger.info(json.dumps(request, indent=4))
    if request_type == "InboundMessage":
        logger.info(json.dumps(request, indent=4))
        wh_message = LeadConnectorWHTypeInboundMessage(**request)
        lc = LeadConnector()
        # lets make sure if ava is suppose to respond to this message
        lc_contact_info = lc.get_contact_info(wh_message.contactId)
        logger.debug(json.dumps(lc_contact_info, indent=4))
        PERMISSION_TAG = "sunny"

        if PERMISSION_TAG not in lc_contact_info["contact"]["tags"]:
            logger.info(
                f"Contact {wh_message.contactId} does not have the permission tag '{PERMISSION_TAG}', cannot engage with the contact"
            )
            return

        # We can engage with the message now
        lc_messages = lc.get_all_messages(wh_message.conversationId)
        message_type = LCMessageType(
            lc_messages[0].type
        )  # getting the first message from the conversation, its the same as the one sent in the webhook

        # lets see if any special code was sent
        RESET_CONVERSATION_CODE = "*RESET#"
        if lc_messages[0].body == RESET_CONVERSATION_CODE:
            logger.info(f"Resetting conversation {wh_message.conversationId}")
            lc.delete_conversation(wh_message.conversationId)
            return None

        # make sure we only get the messages_type we support
        if message_type in [LCMessageType.TYPE_CALL, LCMessageType.TYPE_EMAIL]:
            logger.error(
                f"Recieved message type {message_type}, it is currently not supported"
            )
            return None

        # filtering message by type to make we do not crosscontiminate the messages from different channels
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
        chat_history = chat_messages[1:]
        user_message = chat_messages[0]
        ava_message = ava.chat(user_message, chat_history)
        
        message_split = ava_message.message.content.split("\n\n")
        
        for message in message_split:
            lc.send_message(
                contact_id=wh_message.contactId,
                message=message,
                message_channel=wh_message.messageType,
            )

        # lc.send_message(
        #     contact_id=wh_message.contactId,
        #     message=ava_message.message.content,
        #     message_channel=wh_message.messageType,
        # )

        # lets echo back the message we got
        # logger.debug(f"{wh_message.messageType}")
        # lc.send_message(
        #     contact_id=wh_message.contactId,
        #     message=(wh_message.body + " back!"),
        #     message_channel=wh_message.messageType,
        # )
