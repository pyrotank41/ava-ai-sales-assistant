from fastapi import APIRouter, Depends
from integrations.lead_connector.leadconnector import LeadConnector
from integrations.lead_connector.models import LCCustomField, LCCustomFieldModelType
from security import get_api_key
from fastapi import APIRouter

router = APIRouter()


@router.get("/chat")
async def chat_secure(api_key: str = Depends(get_api_key)):
    return {"message": "Secure chat route accessed"}
