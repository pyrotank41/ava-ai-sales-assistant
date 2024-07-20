from datetime import datetime
import json
from typing import List, Optional
from fastapi import APIRouter, Request
from loguru import logger
from pydantic import BaseModel, Field

from app.services.lead_connector_messaging_service import LeadConnectorMessageingService


class LeadConnectorWHTypeInboundMessage(BaseModel):
    type: str = Field(..., example="InboundMessage")
    locationId: str = Field(..., example="l1C08ntBrFjLS0elLIYU")
    attachments: Optional[List[str]] = Field(..., default_factory=list(), example=[])
    body: str = Field(..., example="This is a test message")
    contactId: str = Field(..., example="cI08i1Bls3iTB9bKgFJh")
    contentType: str = Field(..., example="text/plain")
    conversationId: str = Field(..., example="fcanlLgpbQgQhderivVs")
    dateAdded: datetime = Field(..., example="2021-04-21T11:31:45.750Z")
    direction: str = Field(..., example="inbound")
    messageType: str = Field(..., example="SMS")
    status: str = Field(..., example="delivered")


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
async def leadconnector(request: Request):
    request = await request.json()
    logger.info(f"webhooked by leadconnector location id: {request['locationId']}")

    if not is_lc_location_accepted(request["locationId"]):
        logger.warning(
            f"Location {request['locationId']} not accepted, skipping this WebHook event"
        )
        return

    request_type = request["type"]
    logger.info(f"Leadconnector webhook type {request_type} recieved")

    if request_type == "ContactTagUpdate":
        logger.info(json.dumps(request, indent=4))

    if request_type == "InboundMessage":
        logger.info(json.dumps(request, indent=4))

        wh_message = LeadConnectorWHTypeInboundMessage(**request)
        lc_messaging_service = LeadConnectorMessageingService()

        # if the incomming message is a special code, process it and return, dont go further
        if lc_messaging_service.process_special_codes(
            message=wh_message.body, conversation_id=wh_message.conversationId
        ):
            return

        # if the message is not a special code, respond to the message
        lc_messaging_service.respond_to_inbound_message(
            contact_id=wh_message.contactId, conversation_id=wh_message.conversationId
        )
