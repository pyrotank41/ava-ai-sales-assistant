from datetime import datetime
import json
import os
from typing import List, Optional, Tuple, Union
import sys

from loguru import logger
from pydantic import BaseModel
import pytz

# get the root directory of the project
path = sys.path[0].split("app")[0]
sys.path.append(path)

from services.azure_openai_service import get_azureopenai_service, LeadState
from services.weather_service import WeatherService
from ava.ava import Ava
from datamodel import ChatMessage, ChatResponse

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from timezonefinder import TimezoneFinder
import pytz

def get_timezone_by_city(city: str) -> Optional[str]:
    geolocator = Nominatim(user_agent="my_app")
    tf = TimezoneFinder()
    try:
        location = geolocator.geocode(city)
        if location:
            # Find the timezone for the coordinates
            timezone_str = tf.timezone_at(lat=location.latitude, lng=location.longitude)
            if timezone_str:
                # Return the full timezone name
                return timezone_str
            else:
                logger.debug(f"Could not determine timezone for {city}")
                return None
        else:
            logger.debug(f"Could not find location for {city}")
            return None
    except (GeocoderTimedOut, GeocoderUnavailable):
        print("Error: The geocoding service is unavailable. Please try again later.")
        return None


def format_local_time(dt: datetime) -> str:
    """
    Format a datetime object to a string in the format:
    "Monday, 1:30 pm CDT, 28th July 2024"
    """
    # Format the day of the week
    day_of_week = dt.strftime("%A")

    # Format the time
    time_str = dt.strftime("%I:%M %p")
    time_str = time_str.lstrip("0")  # Remove leading zero from hour

    # Get the timezone abbreviation
    timezone_str = dt.strftime("%Z")

    # Format the date
    date_str = dt.strftime("%d{} %B %Y").format(
        "th"
        if 11 <= dt.day <= 13
        else {1: "st", 2: "nd", 3: "rd"}.get(dt.day % 10, "th")
    )

    return f"{day_of_week}, {time_str} {timezone_str}, {date_str}"


def get_local_time(timezone: str) -> Optional[datetime]:
    try:
        tz = pytz.timezone(timezone)
        return datetime.now(tz)
    except pytz.exceptions.UnknownTimeZoneError:
        logger.error(f"Unknown timezone: {timezone}")
        return None


def get_weather(city: str):
    weather_service = WeatherService(os.getenv("OPENWEATHER_API_KEY"))
    try:
        return weather_service.get_weather_by_city(city)
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        return None

    # usage example
    # weather = None if city is None else get_weather(city)
    # weather_info = (
    #     f"Weather: {weather['description']}, Temperature: {weather['temperature']}°F"
    #     if weather
    #     else "information unavailable"
    # )


def load_prompt_template(file_path: str) -> str:
    with open(file_path, "r") as file:
        return file.read()


def get_timezone(timezone, city):
    if timezone is None:
        logger.warning(
            "Timezone not in contact_info, trying to determine timezone from city"
        )
        if city is not None:
            timezone = get_timezone_by_city(city)
            logger.info(f"Timezone determined from city: {timezone}")
        else:
            logger.warning("City not in contact_info, timezone will be None")

    # validate the timezone
    if timezone is not None:
        try:
            pytz.timezone(timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.error(f"Unknown timezone: {timezone}")
            timezone = None
    return timezone


def get_time_in_contact_timezone(timezone: str):
    local_time = None if timezone is None else get_local_time(timezone)
    return local_time


class ContactInfo(BaseModel):
    id: str
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    timezone: Optional[str] = None
    lead_state: Optional[str] = None
    pre_qualification_qa: Optional[dict] = {}


def format_pre_qualification_qa(pre_qualification_qa: Optional[dict]) -> str:
    if pre_qualification_qa is None or len(pre_qualification_qa) == 0:
        return "No pre-qualification information available."

    formatted_qa = []
    for key, value in pre_qualification_qa.items():
        formatted_key = key.replace("_", " ").title()
        formatted_qa.append(f"- {formatted_key}: {value}")

    return "\n".join(formatted_qa)


def get_lead_state_description(join_string: str = "\n    "):
    lead_state_descriptions = {
        "COLD": "The lead shows no interest or engagement.",
        "WARMING_UP": "The lead is showing some interest but is not yet fully engaged.",
        "INTERESTED": "The lead is actively engaged and showing strong interest.",
        "READY_FOR_APPOINTMENT": "The lead is ready to schedule an appointment or take the next step.",
        "NOT_INTERESTED": "The lead has explicitly expressed lack of interest.",
    }
    return (join_string).join(
        [f"{key}: {value}" for key, value in lead_state_descriptions.items()]
    )

def get_context(contact_info: ContactInfo, local_time: Optional[datetime], lead_state: str):
    context = f"""
About the lead:
- First_Name: {contact_info.first_name if contact_info.first_name is not None else "Not provided"}
- Last_Name: {contact_info.last_name if contact_info.last_name is not None else "Not provided"}
- Address: {contact_info.address if contact_info.address is not None else "Not provided"}
- City: {contact_info.city if contact_info.city is not None else "Not provided"}
- State: {contact_info.state if contact_info.state is not None else "Not provided"}

Lead State Information:
- Current_State: {lead_state if lead_state is not None else "Not specified"}
- State_Description: 
    {get_lead_state_description()}

Pre-qualification Information:
{format_pre_qualification_qa(contact_info.pre_qualification_qa)}

Spatial Information:
- Local_Time: {format_local_time(local_time) if local_time is not None else "Information unavailable"}
        """

    logger.debug(f"Context message: {context}")
    return context


class AvaService:
    def __init__(self):
        self.ava = Ava(system_message="hello")
        self.openai_service = get_azureopenai_service()

    def respond(
        self,
        contact_info: ContactInfo,
        conversation_messages: List[ChatMessage] = list(),
    ) -> Tuple[bool, str]:
        """
        Generates a message for a lead based on their contact information, chat history, and current state.

        Args:
            contact_info (dict): A dictionary containing the contact information of the lead.
            chat_history (List[ChatMessage]): A list of previous chat messages with the lead.
            user_message (Optional[ChatMessage], optional): The user's message to the lead. Defaults to None.

        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating the success of message generation and the generated message.

        Raises:
            Exception: If an error occurs while generating the message.

        """

        if not isinstance(contact_info, ContactInfo):
            logger.error("contact_info must be of type ContactInfo")

        # if len(conversation_messages) > 0:
        #     most_recent_message = conversation_messages[-1]
        #     user_message = most_recent_message.content if most_recent_message.role == "user" else None
        #     chat_history = conversation_messages[:-1]


        # collecting metadata for the lead
        time_zone = contact_info.timezone
        contact_city = contact_info.city

        time_zone = get_timezone(time_zone, contact_city)
        local_time = get_local_time(time_zone) if time_zone is not None else None

        # understand the sales state of the lead
        lead_state = self.openai_service.determine_lead_state(
            conversation_history=[message.dict() for message in conversation_messages]
        )

        # Creating the context message
        prompt_template = load_prompt_template("prompt/lead_engage_sms.txt")

        context_message = get_context(contact_info, local_time, lead_state)


        if lead_state != LeadState.READY_FOR_APPOINTMENT:
            try:
                system_message = prompt_template.format(context=context_message)
                logger.debug(f"System message: {system_message}")

                rep = self.ava.respond(
                    conversation_messages=conversation_messages,
                    system_message=system_message,
                )
                return (True, rep.message.content)
               
            except Exception as e:
                logger.error(f"Error generating message: {e}")
                return (
                    False,
                    f"An error occurred while generating the message for contact {contact_info.get('id')}.",
                )
        else:
            return (
                False,
                f"The lead {contact_info} is ready for an appointment, please schedule one.",
            )


if __name__ == "__main__":

    # test 1 empty conversation history
    ava_service = AvaService()
    dummy_contact = {
        "id": "3fnq8LpXHRtBvMzS5Ykd",
        "full_name": "Taylor Johnson",
        "first_name": "Taylor",
        "last_name": "Johnson",
        "address": "1472 Prairie Lane, Springfield, IL, 62701, United States",
        "city": "Springfield",
        "state": "IL",
        "timezone": None,
        "lead_state": None,
        "pre_qualification_qa": {
            "roof_age": "5_to_10_years",
            "credit_score": "680_to_719",
            "average_monthly_electric_bill": "$100_to_$150",
            "annual_household_income": "$60,000_to_$80,000",
            "homeowner": "yes",
        },
    }
    dummy_contact = ContactInfo(**dummy_contact)
    resp = ava_service.respond(dummy_contact, conversation_messages=[])
    logger.info(resp)
   