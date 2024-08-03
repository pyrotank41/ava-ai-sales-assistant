from typing import Any, Dict, Optional
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import requests

def get_city_coordinates(city_name, country_code="US"):
    # Initialize the geocoder
    geolocator = Nominatim(user_agent="my_app")

    try:
        # Attempt to geocode the city
        location = geolocator.geocode(f"{city_name}", country_codes=country_code)

        if location:
            return (location.latitude, location.longitude)
        else:
            return None
    except (GeocoderTimedOut, GeocoderUnavailable):
        print("Error: The geocoding service is unavailable. Please try again later.")
        return None


class WeatherService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/3.0/onecall"

    def get_weather(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        params = {
            "lat": lat,
            "lon": lon,
            "exclude": "minutely,hourly,daily,alerts",  # We only need current weather
            "appid": self.api_key,
            "units": "imperial",
        }
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            return {
                "description": data["current"]["weather"][0]["description"],
                "temperature": data["current"]["temp"],
            }
        except requests.RequestException as e:
            print(f"Error fetching weather data: {e}")
            return None

    def get_weather_by_city(self, city: str) -> Optional[Dict[str, Any]]:
        coordinates = get_city_coordinates(city)
        if coordinates is None:
            return None
        lat, lon = coordinates
        return self.get_weather(lat, lon)
