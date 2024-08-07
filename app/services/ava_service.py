from datetime import datetime
import json
import os
from typing import List, Optional, Tuple
import sys

from loguru import logger
import pytz

# get the root directory of the project
path = sys.path[0].split("app")[0]
sys.path.append(path)

from services.azure_openai_service import get_azureopenai_service, LeadState
from services.weather_service import WeatherService
from ava.ava import Ava
from datamodel import ChatMessage,ChatResponse

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from timezonefinder import TimezoneFinder
import pytz

# def get_timezone_by_city(city: str) -> Optional[str]:
#     geolocator = Nominatim(user_agent="my_app")
#     tf = TimezoneFinder()
#     try:
#         location = geolocator.geocode(city)
#         # Find the timezone for the coordinates
#         timezone_str = tf.timezone_at(lat=location.latitude, lng=location.longitude)

#         if timezone_str:
#             # Get the timezone object
#             tz = pytz.timezone(timezone_str)
#             # Return the current time in that timezone
#             return str(datetime.now(tz).tzname())
#         else:
#             print(f"Could not determine timezone for {city}")
#             return None

#     except (GeocoderTimedOut, GeocoderUnavailable):
#         print("Error: The geocoding service is unavailable. Please try again later.")
#         return None

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
    "1:30 pm CDT, 28th July 2024"
    """
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

    return f"{time_str} {timezone_str}, {date_str}"


def get_local_time(timezone: str) -> Optional[datetime]:
    try:
        tz = pytz.timezone(timezone)
        return datetime.now(tz)
    except pytz.exceptions.UnknownTimeZoneError:
        logger.error(f"Unknown timezone: {timezone}")
        return None


def get_weather(city:str):
    weather_service = WeatherService(os.getenv("OPENWEATHER_API_KEY"))
    try:
        return weather_service.get_weather_by_city(city)
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        return None


def load_prompt_template(file_path: str) -> str:
    with open(file_path, "r") as file:
        return file.read()


class AvaService:
    def __init__(self):
        self.ava = Ava(
            system_message="hello"
        )
        self.openai_service = get_azureopenai_service()

    def generate_message(
        self,
        contact_info: dict,
        chat_history: List[ChatMessage],
        user_message: Optional[ChatMessage] = None,
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
        if not isinstance(contact_info, dict):
            logger.error("contact_info must be a dictionary")

        # collecting metadata for the lead
        time_zone = contact_info.get("timezone")
        contact_city = contact_info.get("city")

        if time_zone is None:
            logger.warning("Timezone not in contact_info, trying to determine timezone from city")
            if contact_city is not None:
                time_zone = get_timezone_by_city(contact_city)
            else:
                logger.warning("City not in contact_info, timezone will be None")

        local_time = None if time_zone is None else get_local_time(time_zone)
        weather = None if contact_city is None else get_weather(contact_city)
        lead_state = self.openai_service.determine_lead_state(
            conversation_history=[message.dict() for message in chat_history])

        weather_info = (
            f"Weather: {weather['description']}, Temperature: {weather['temperature']}°F"
            if weather
            else "information unavailable"
        )

        # Creating the context message
        prompt_template = load_prompt_template("app/prompt/lead_engage_sms.txt")

        context_message = f"""
        About the lead: 
        contact_info: {contact_info}
        lead_state: {lead_state}
        
        Spacial information:
        weather_info: {weather_info}
        local_time: {format_local_time(local_time) if local_time is not None else "information unavailable"}
        """
        logger.info(f"Context message: {context_message}")

        if lead_state != LeadState.READY_FOR_APPOINTMENT:
            try:
                if user_message is None:
                    context_message += f"""
                    conversational history: 
                    {[message.dict() for message in chat_history]}
                    """

                    context = prompt_template.format(context=context_message)
                    user_message = "Generate a personalized message for this lead, considering their current state, using appropriate sales techniques."
                    resp = self.openai_service.generate_response(context, user_message)
                    logger.info(f"Generated response: {resp}")
                    return True, resp
                else:
                    context = prompt_template.format(context=context_message)
                    resp = self.ava.chat(user_message, chat_history, system_message=context)
                    return True, resp.message.content
            
            except Exception as e:
                logger.error(f"Error generating message: {e}")
                return False, f"An error occurred while generating the message for contact {contact_info.get('id')}."
        else: 
            return False, f"The lead {contact_info} is ready for an appointment, please schedule one."

if __name__ == "__main__":
    ava_service = AvaService()
    logger.info(ava_service.generate_message(contact_info={"name": "john", "city": "bollingbrook"}, chat_history=[]))
    # user_message = ChatMessage(role="user", content="Hello")
    # chat_history = []
    # contact_info = {}
    # response = ava_service.generate_message(user_message, chat_history, contact_info
