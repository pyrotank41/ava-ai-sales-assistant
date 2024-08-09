from integrations.lead_connector.leadconnector import LeadConnector
from integrations.lead_connector.models import LCCustomField
from security import get_api_key

from fastapi import APIRouter, Depends

router = APIRouter()


@router.get("/contact")
async def get_contact():
    return LeadConnector(location_id="hqDwtNvswsupf6BT1Qxt").get_contact_info(
        contact_id="6ygr3QkYGJfEGfNJ2FvD"
    )


@router.get("/custom_fields")
async def get_custom_fields(location_id):
    return LeadConnector(location_id=location_id).get_custom_fields()
    
@router.get("/custom_fields/id_key_mapping")
async def get_custom_fields_id_key_mapping(location_id):
    return LeadConnector(location_id=location_id).get_custom_fields_id_key_mapping()

