import os
import time
from loguru import logger
from openai import AzureOpenAI
from enum import Enum
from datetime import datetime
import pytz
import requests
import json
from typing import Dict, List, Optional, Any, Protocol, Tuple

import sys

path = sys.path[0].split("app")[0]
sys.path.append(path)
from app.services.weather_service import WeatherService
from app.services.azure_openai_service import AzureOpenAIService, LeadState, OpenAIServiceInterface


# Interfaces
class WeatherServiceInterface(Protocol):
    def get_weather(self, city: str) -> Optional[Dict[str, Any]]: ...


class CRMServiceInterface(Protocol):
    def get_contact_info(self, contact_id: str) -> Dict[str, Any]: ...
    def get_conversation_history(self, contact_id: str) -> List[Dict[str, str]]: ...
    def send_message_to_lead(self, contact_id: str, message: str) -> None: ...
    def get_lead_response(self, contact_id: str) -> str: ...
    def update_lead_state(self, contact_id: str, new_state: LeadState) -> None: ...
    def notify_lead_owner(self, contact_id: str) -> None: ...


# Utility functions
def get_local_time(timezone: str) -> datetime:
    tz = pytz.timezone(timezone)
    return datetime.now(tz)


def load_prompt_template(file_path: str) -> str:
    with open(file_path, "r") as file:
        return file.read()


class CRMService:
    def __init__(self):
        # In a real implementation, you would initialize your CRM client here
        self.leads_db = {}  # This is a mock database for demonstration purposes

    def get_contact_info(self, contact_id: str) -> Dict[str, Any]:
        # In a real implementation, you would fetch this from your CRM
        if contact_id not in self.leads_db:
            self.leads_db[contact_id] = {
                "name": f"john doe",
                "email": f"johndoe@example.com",
                "timezone": "America/New_York",
                "city": "New York",
                "state": "New York",
                "conversation_history": [],
            }
        return self.leads_db[contact_id]

    def get_conversation_history(self, contact_id: str) -> List[Dict[str, str]]:
        return self.leads_db.get(contact_id, {}).get("conversation_history", [])

    def send_message_to_lead(self, contact_id: str, message: str) -> None:
        if contact_id not in self.leads_db:
            raise ValueError(f"Contact {contact_id} not found")
        self.leads_db[contact_id]["conversation_history"].append(
            {"role": "assistant", "content": message}
        )
        print(f"Message sent to {contact_id}: {message}")

    def get_lead_response(self, contact_id: str) -> str:
        # In a real implementation, you would wait for an actual response
        # Here, we're simulating a delay and returning a mock response
        time.sleep(2)  # Simulate waiting for a response
        mock_responses = [
            "Tell me more about your solar panels.",
            "What are the costs involved?",
            "I'm not interested at this time.",
            "Can we schedule an appointment?",
            "Thanks for the information.",
        ]
        response = mock_responses[hash(contact_id) % len(mock_responses)]
        self.leads_db[contact_id]["conversation_history"].append(
            {"role": "user", "content": response}
        )
        logger.debug(f"Lead response received: {response}")
        return response

    def update_lead_state(self, contact_id: str, new_state: LeadState) -> None:
        if contact_id not in self.leads_db:
            raise ValueError(f"Contact {contact_id} not found")
        self.leads_db[contact_id]["state"] = new_state
        print(f"Lead {contact_id} state updated to {new_state.name}")

    def notify_lead_owner(self, contact_id: str) -> None:
        # In a real implementation, you would send a notification to the lead owner
        print(f"Notifying lead owner: Lead {contact_id} is ready for an appointment")

class AISalesAssistant:
    def __init__(
        self,
        weather_service: WeatherService,
        openai_service: OpenAIServiceInterface,
        crm_service: CRMServiceInterface,
        prompt_file_path: str,
    ):
        self.weather_service = weather_service
        self.openai_service = openai_service
        self.crm_service = crm_service
        self.prompt_template = load_prompt_template(prompt_file_path)

    def engage_contact(self, contact_id: str) -> str:

        contact_info = self.crm_service.get_contact_info(contact_id)

        conversation_history = self.crm_service.get_conversation_history(contact_id)
        lead_state = self.openai_service.determine_lead_state(conversation_history)

        local_time = get_local_time(contact_info["timezone"])
        weather = self.weather_service.get_weather_by_city(contact_info["city"])
        # weather = self.weather_service.get_weather(*coordinates)

        response = self.generate_response(
            contact_info, conversation_history, lead_state, local_time, weather
        )
        self.crm_service.send_message_to_lead(contact_id, response)

        lead_response = self.crm_service.get_lead_response(contact_id)
        new_lead_state = self.openai_service.determine_lead_state(
            conversation_history + [{"role": "user", "content": lead_response}]
        )

        if new_lead_state == LeadState.READY_FOR_APPOINTMENT:
            self.crm_service.notify_lead_owner(contact_id)
            return "Lead is ready for appointment. Lead owner notified."

        self.crm_service.update_lead_state(contact_id, new_lead_state)
        return "Message sent to lead. Awaiting next interaction."

    def generate_response(
        self,
        contact_info: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
        lead_state: LeadState,
        local_time: datetime,
        weather: Optional[Dict[str, Any]],
    ) -> str:

        weather_info = (
            f"Weather: {weather['description']}, Temperature: {weather['temperature']}°C"
            if weather
            else "Weather information unavailable"
        )

        context = self.prompt_template.format(
            contact_info=contact_info,
            conversation_history=conversation_history,
            lead_state=lead_state.name,
            local_time=local_time.strftime("%A, %B %d, %Y, %I:%M %p"),
            weather_info=weather_info,
        )

        return self.openai_service.generate_response(
            context,
            "Generate a personalized message for this lead, considering their current state, local time, weather, and using appropriate sales techniques.",
        )


# Usage example:
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")
    azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    azure_chat_model = os.getenv("AZURE_OPENAI_CHAT_MODEL", "gpt-4o")
    azure_analysis_model = os.getenv("AZURE_OPENAI_ANALYSIS_MODEL", "gpt-4o")

    if not all(
        [
            azure_endpoint,
            azure_api_key,
            azure_api_version,
            azure_chat_model,
            azure_analysis_model,
            deployment_name
        ]
    ):
        raise ValueError(
            "Azure OpenAI configuration is incomplete. Please check your environment variables."
        )

    weather_service = WeatherService(os.getenv("OPENWEATHER_API_KEY"))
    # logger.info("Weather service initialized")

    # city = "New York"
    # country_code = "US"
    # coordinates = weather_service.get_coordinates(city, country_code)
    # logger.info(weather_service.get_weather(*coordinates))
    openai_service = AzureOpenAIService(
        azure_endpoint,
        azure_api_key,
        azure_api_version,
        azure_chat_model,
        azure_analysis_model,
    )

    # openai_service.health_check(azure_chat_model)

    crm_service = CRMService()

    assistant = AISalesAssistant(
        weather_service=weather_service,
        openai_service=openai_service,
        crm_service=crm_service,
        prompt_file_path="app/prompt/lead_engage_sms.txt",
    )
    result = assistant.engage_contact("example_contact_id")
    print(result)
