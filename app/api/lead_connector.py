from integrations.lead_connector.leadconnector import LeadConnector
from integrations.lead_connector.models import LCCustomField, LCMessageType
from security import get_api_key

from fastapi import APIRouter, Depends

from services.lead_connector_messaging_service import LeadConnectorMessageingService

router = APIRouter()

@router.get("/engage_contact")
def engage_contact(contact_id, location_id, message_type:LCMessageType = LCMessageType.TYPE_SMS):
    return LeadConnectorMessageingService(location_id=location_id).engage_with_contact(contact_id=contact_id, message_type=message_type)

@router.get("/contact")
def get_contact():
    return LeadConnector(location_id="hqDwtNvswsupf6BT1Qxt").get_contact_info(
        contact_id="6ygr3QkYGJfEGfNJ2FvD"
    )

@router.get("/custom_fields")
def get_custom_fields(location_id):
    return LeadConnector(location_id=location_id).get_custom_fields()
    
@router.get("/custom_fields/id_key_mapping")
def get_custom_fields_id_key_mapping(location_id):
    return LeadConnector(location_id=location_id).get_custom_fields_id_key_mapping()

