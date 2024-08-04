from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
import os

from utils.load_env import load_env_vars

def load_api_keys():
    #check if the api keys are set in the environment
    key1 = os.getenv("API_KEY1")
    key2 = os.getenv("API_KEY2")

    if not key1 or not key2:
        # load from remote storage
        load_env_vars()
        key1, key2 = load_api_keys()

    # final validation
    if not key1 or not key2:
        raise ValueError("API_KEY1 and API_KEY2 must be set in the environment")

    return key1, key2

API_KEY1, API_KEY2 = load_api_keys()
API_KEY_NAME = "access_token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header in (API_KEY1, API_KEY2):
        return api_key_header
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate API key"
        )
