from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
import os
from utils.env import load_env_vars



def load_api_keys():
    
    # Check if the API keys are set in the environment
    key1 = os.getenv("API_KEY1")
    key2 = os.getenv("API_KEY2")

    if not key1 or not key2:
        # Load from remote storage
        load_env_vars()

        # Check again after loading from remote storage
        key1 = os.getenv("API_KEY1")
        key2 = os.getenv("API_KEY2")

    # Final validation
    if not key1 or not key2:
        raise ValueError("API_KEY1 and API_KEY2 must be set in the environment")

    return key1, key2


API_KEY1, API_KEY2 = load_api_keys()
API_KEY_NAME = "access_token"

def get_api_key(
    api_key_header: str = Security(APIKeyHeader(name=API_KEY_NAME, auto_error=False))
):
    if api_key_header in (API_KEY1, API_KEY2):
        return api_key_header
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate API key"
        )
