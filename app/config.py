from pydantic_settings import BaseSettings


# class Settings(BaseSettings):
#     ava_api_key: str
#     clerk_api_key: str
#     gohighlevel_api_key: str
#     whatsapp_api_key: str

#     class Config:
#         env_file = ".env"


# settings = Settings()


PERMISSION_TAG = "sunny"
MAX_CONVERSATION_COUNT = 15

AVA_ENGAGED_TAG = "AVA-Engaged"
AVA_INTERACTED_TAG = "AVA-Interacted"
AVA_MAX_SMS_CONVO_REACHED = "AVA-MaxSMSConvoReached"

GHL_CUSTOM_FIELD_NUMBER_OF_INTERACTION_KEY = "contact.number_of_interactions"
GHL_CUSTOM_FIELD_LEAD_STATE_KEY = "contact.lead_state"
