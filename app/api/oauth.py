import json
from fastapi import APIRouter, Request
from app.integrations.leadconnector import get_auth_url, get_and_save_token

router = APIRouter()

@router.get("/login/leadconnector")
async def login():
    url = get_auth_url()
    return {"url": url}


@router.get("/callback/leadconnector")
async def callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    await get_and_save_token(code, state)
    return {"message": "successessfully authenticated with leadconnector"}
