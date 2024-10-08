from datetime import datetime
import json
from typing import List, Optional
from fastapi import APIRouter, Request
from loguru import logger
from pydantic import BaseModel, Field

from config import AGENT_ENGAGED_TAG
from integrations.lead_connector.leadconnector import LeadConnector
from services.lead_connector_messaging_service import LeadConnectorMessageingService


class LeadConnectorWHTypeInboundMessage(BaseModel):
    type: str = Field(..., example="InboundMessage")
    locationId: str = Field(..., example="l1C08ntBrFjLS0elLIYU")
    attachments: Optional[List[str]] = list()
    body: Optional[str] = Field(None, example="This is a test message")
    contactId: Optional[str] = Field(None, example="cI08i1Bls3iTB9bKgFJh")
    contentType: Optional[str] = Field(None, example="text/plain")
    conversationId: Optional[str] = Field(None, example="fcanlLgpbQgQhderivVs")
    dateAdded: Optional[datetime] = Field(None, example="2021-04-21T11:31:45.750Z")
    direction: Optional[str] = Field(None, example="inbound")
    messageType: Optional[str] = Field(None, example="SMS")
    status: Optional[str] = Field(None, example="delivered")


router = APIRouter()


def is_lc_location_accepted(location_id: str) -> bool:
    """
    Check if a location is accepted based on its ID.

    Args:
        location_id (str): The ID of the location to check.

    Returns:
        bool: True if the location is accepted, False otherwise.
    """
    file_path = ".config/accepted_locations.json"

    try:
        with open(file_path, "r") as file:
            file_data = json.load(file)
            accepted_locations = file_data["locations"]
    except FileNotFoundError as exc:
        logger.error("File not found")
        raise FileNotFoundError("File not found") from exc

    if location_id in accepted_locations:
        return True
    else:
        return False


@router.post("/leadconnector")
def leadconnector(request: Request):
    request = request.json()
    logger.info(f"webhooked by leadconnector location id: {request['locationId']}")

    # if not is_lc_location_accepted(request["locationId"]):
    if request["locationId"] not in ["hqDwtNvswsupf6BT1Qxt"]:
        logger.warning(
            f"Location {request['locationId']} not accepted, skipping this WebHook event"
        )
        return

    request_type = request["type"]
    logger.info(f"Leadconnector webhook type {request_type} recieved")

    if request_type == "ContactTagUpdate":
        logger.info(json.dumps(request, indent=4))      

    if request_type == "OutboundMessage":
        leadconnector = LeadConnector(location_id=request["locationId"])
        contact_id = request["contactId"]
        message_type = request["messageType"]

        if message_type == "SMS": 
            # this is so that we know that agnet responded the contact,
            # we will use this tag later to nor respond to the contact
            leadconnector.add_tag_to_contact(contact_id, AGENT_ENGAGED_TAG)

    if request_type == "InboundMessage":
        logger.info(json.dumps(request, indent=4))

        wh_message = LeadConnectorWHTypeInboundMessage(**request)
        lc_messaging_service = LeadConnectorMessageingService(
            location_id=wh_message.locationId
        )

        # if the incomming message is a special code, process it and return, dont go further
        if lc_messaging_service.process_special_codes(
            message=wh_message.body, conversation_id=wh_message.conversationId
        ):
            return
        # if the message is not a special code, respond to the message
        lc_messaging_service.process_to_inbound_message(
            contact_id=wh_message.contactId,
            conversation_id=wh_message.conversationId,
        )
