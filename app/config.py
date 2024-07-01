from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ava_api_key: str
    clerk_api_key: str
    gohighlevel_api_key: str
    whatsapp_api_key: str

    class Config:
        env_file = ".env"


settings = Settings()
