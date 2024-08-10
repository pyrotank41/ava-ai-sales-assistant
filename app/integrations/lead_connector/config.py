import os
from loguru import logger
from utils.env import is_dev_env

CLIENT_ID = os.getenv("LEADCONNECTOR_CLIENT_ID")
CLIENT_SECRET = os.getenv("LEADCONNECTOR_CLIENT_SECRET")

if is_dev_env():
    REDIRECT_URI = "http://localhost:8080/oauth/callback/leadconnector"
else: 
    REDIRECT_URI = os.getenv("LEADCONNECTOR_REDIRECT_URI")

logger.info(
    f"Lead Connector configuration: CLIENT_ID:{CLIENT_ID[:4]}***, CLIENT_SECRET: {CLIENT_SECRET[:4]}****{CLIENT_SECRET[-4:]}, TOKEN_URL:{REDIRECT_URI}"
)


if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
    raise ValueError("LEADCONNECTOR_CLIENT_ID, LEADCONNECTOR_CLIENT_SECRET, and LEADCONNECTOR_REDIRECT_URI must be set in the environment variables")

AUTHORIZATION_URL = "https://marketplace.leadconnectorhq.com/oauth/chooselocation"
TOKEN_URL = "https://services.leadconnectorhq.com/oauth/token"  # url to get the token using the code from the authorization url
