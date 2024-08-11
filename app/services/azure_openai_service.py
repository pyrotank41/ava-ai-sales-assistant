from enum import Enum
import json
import os
from typing import Dict, List, Protocol
from dotenv import load_dotenv
from loguru import logger
from openai import AzureOpenAI


class LeadState(str, Enum):
    COLD = "cold"
    WARMING_UP = "warming_up"
    INTERESTED = "interested"
    READY_FOR_APPOINTMENT = "ready_for_appointment"
    NOT_INTERESTED = "not_interested"


class OpenAIServiceInterface(Protocol):
    def generate_response(self, context: str, user_message: str) -> str: ...
    def determine_lead_state(
        self, conversation_history: List[Dict[str, str]]
    ) -> LeadState: ...


class AzureOpenAIService:
    def __init__(
        self,
        azure_endpoint: str,
        api_key: str,
        api_version: str,
        chat_model: str,
        analysis_model: str,
    ):
        self.client = AzureOpenAI(
            azure_endpoint=azure_endpoint, api_key=api_key, api_version=api_version
        )
        self.chat_model = chat_model
        self.analysis_model = analysis_model
        
    def get_client(self):
        return self.client

    def health_check(self, model: str) -> str:
        try:
            resp = self.client.chat.completions.create(
                temperature=0.0,
                model=model,
                messages=[{"role": "system", "content": "hello"}],
            )
            logger.debug(f"Health check response: {resp.choices[0].message.content}")
            return "Health check successful"
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            raise ValueError(f"Error in health check: {e}") from e

    def generate_response(self, context: str, user_message: str) -> str:
        response = self.client.chat.completions.create(
            temperature=0.5,
            model=self.chat_model,
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content

    def determine_lead_state(
        self, conversation_history: List[Dict[str, str]]
    ) -> LeadState:
        prompt = f"""
            Analyze the following conversation history and determine the lead's current state.
            The possible states are:
            - COLD: The lead shows no interest or engagement.
            - WARMING_UP: The lead is showing some interest but is not yet fully engaged.
            - INTERESTED: The lead is actively engaged and showing strong interest.
            - READY_FOR_APPOINTMENT: The lead is ready to schedule an appointment or take the next step.
            - NOT_INTERESTED: The lead has explicitly expressed lack of interest.

            Conversation history:
            {conversation_history}

            Based on this conversation, what is the current state of the lead? 
            Respond with a JSON object in the following format:
            {{"lead_state": "STATE_NAME"}}
            Where STATE_NAME is one of the states listed above.
            """

        try:
            response = self.client.chat.completions.create(
                model=self.analysis_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=50,
                temperature=0
            )

            result = json.loads(response.choices[0].message.content)
            state_str = result.get("lead_state", "").upper()

            if state_str in LeadState.__members__:
                return LeadState[state_str]
            else:
                raise ValueError(f"Invalid lead state returned: {state_str}")

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error in determining lead state: {e}")
            # Default to COLD if there's any error in parsing or invalid state
            return LeadState.COLD


def get_azureopenai_service():
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
    
    
    service = AzureOpenAIService(
        azure_endpoint,
        azure_api_key,
        azure_api_version,
        azure_chat_model,
        azure_analysis_model,
    )
    
    return service

if __name__ == "__main__":
    from pydantic import BaseModel
    from openai import OpenAI

    client = get_azureopenai_service().client

    class Step(BaseModel):
        explanation: str
        output: str

    class MathReasoning(BaseModel):
        steps: list[Step]
        final_answer: str

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful math tutor. Guide the user through the solution step by step. respond in json format. {'response': 'your response here'}",
            },
            {"role": "user", "content": ""},
        ],
        response_format={"type": "json_object"},
    )

    print(completion.choices[0].message.content)
