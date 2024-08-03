from fastapi import APIRouter, Depends
from security import get_api_key
from fastapi import APIRouter

router = APIRouter()

@router.get("/chat")
async def chat_secure(api_key: str = Depends(get_api_key)):
    return {"message": "Secure chat route accessed"}
