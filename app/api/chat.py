from fastapi import APIRouter, Depends
from app.security import get_api_key

router = APIRouter()


@router.get("/chat-secure")
async def chat_secure(api_key: str = Depends(get_api_key)):
    return {"message": "Secure chat route accessed"}


@router.get("/chat-public")
async def chat_public():
    return {"message": "Public chat route accessed"}
