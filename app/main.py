import os
from fastapi import FastAPI
from api import ava
from api import oauth
from api import webhook
from fastapi.openapi.utils import get_openapi
from utils.load_env import load_env_vars

load_env_vars()


app = FastAPI()

app.include_router(oauth.router, tags=["Integration authentications"], prefix="/oauth")
app.include_router(ava.router, tags=["Ava api endpoint"], prefix="/ava")
app.include_router(webhook.router, tags=["Webhook endpoint"], prefix="/webhook")

# add a health check endpoint /health
@app.get("/health")
async def health():
    return {"status": "ok"}

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
