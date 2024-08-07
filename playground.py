# from geopy.geocoders import Nominatim
# from geopy.exc import GeocoderTimedOut, GeocoderUnavailable


# def get_city_coordinates(city_name):
#     # Initialize the geocoder
#     geolocator = Nominatim(user_agent="my_app")

#     try:
#         # Attempt to geocode the city
#         location = geolocator.geocode(city_name)

#         if location:
#             return (location.latitude, location.longitude)
#         else:
#             return None
#     except (GeocoderTimedOut, GeocoderUnavailable):
#         print("Error: The geocoding service is unavailable. Please try again later.")
#         return None


# # Example usage
# city = input("Enter a city name: ")
# coordinates = get_city_coordinates(city)

# if coordinates:
#     print(f"The coordinates of {city} are: {coordinates}")
# else:
#     print(f"Could not find coordinates for {city}")


from openai import OpenAI
from portkey_ai import PORTKEY_GATEWAY_URL, createHeaders

client = OpenAI(
    api_key="",
    base_url=PORTKEY_GATEWAY_URL,
    default_headers=createHeaders(
        provider="openai", api_key=""
    ),
)

chat_complete = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "What's a Fractal?"}],
)

print(chat_complete.choices[0].message.content)
