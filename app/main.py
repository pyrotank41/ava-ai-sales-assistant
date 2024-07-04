from fastapi import FastAPI
from app.api import ava
from app.api import oauth
from app.api import webhook
from fastapi.openapi.utils import get_openapi
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

app.include_router(oauth.router, tags=["Integration authentications"], prefix="/oauth")
app.include_router(ava.router, tags=["Ava api endpoint"], prefix="/ava")
app.include_router(webhook.router, tags=["Webhook endpoint"], prefix="/webhook")

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Artificial Virtual Assistant API",
        version="1.0.0",
        description="AVA is a virtual assistant that can help you with your inbount and outbound reach. currently limited to text chat via API and Gohighlevel integration.",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "APIKeyHeader": {"type": "apiKey", "name": "access_token", "in": "header"}
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"APIKeyHeader": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
