import os


CLIENT_ID = os.getenv("LEADCONNECTOR_CLIENT_ID")
CLIENT_SECRET = os.getenv("LEADCONNECTOR_CLIENT_SECRET")
REDIRECT_URI = os.getenv("LEADCONNECTOR_REDIRECT_URI")

if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
    raise ValueError("LEADCONNECTOR_CLIENT_ID, LEADCONNECTOR_CLIENT_SECRET, and LEADCONNECTOR_REDIRECT_URI must be set in the environment variables")

AUTHORIZATION_URL = "https://marketplace.leadconnectorhq.com/oauth/chooselocation"
TOKEN_URL = "https://services.leadconnectorhq.com/oauth/token"  # url to get the token using the code from the authorization url
