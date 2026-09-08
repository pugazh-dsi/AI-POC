"""Current weather via Open-Meteo.

Deliberately keyless: Open-Meteo's geocoding and forecast endpoints need no
credentials, so the Tool Calling tile demos a real external API call without a
second key to configure. Two hops — name → coordinates, coordinates → weather.
"""

import httpx

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 10.0

# WMO weather interpretation codes (the API returns a number, not a description)
WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "depositing rime fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    56: "light freezing drizzle", 57: "dense freezing drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    66: "light freezing rain", 67: "heavy freezing rain",
    71: "slight snowfall", 73: "moderate snowfall", 75: "heavy snowfall",
    77: "snow grains",
    80: "slight rain showers", 81: "moderate rain showers", 82: "violent rain showers",
    85: "slight snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


def get_weather(city: str, units: str = "celsius") -> dict:
    """Look up the current weather for a city."""
    city = (city or "").strip()
    if not city:
        return {"error": "No city provided."}

    units = units if units in ("celsius", "fahrenheit") else "celsius"

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            geo = client.get(
                GEOCODE_URL, params={"name": city, "count": 1, "format": "json"}
            )
            geo.raise_for_status()
            places = geo.json().get("results") or []

            if not places:
                return {"error": f"Could not find a place called '{city}'."}

            place = places[0]
            forecast = client.get(FORECAST_URL, params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                           "precipitation,weather_code,wind_speed_10m",
                "temperature_unit": units,
                "wind_speed_unit": "kmh",
                "timezone": "auto",
            })
            forecast.raise_for_status()
            data = forecast.json()
    except httpx.HTTPError as e:
        # Reported as data, not raised: the model sees the failure and can tell
        # the user rather than the whole turn dying.
        return {"error": f"Weather lookup failed: {e}"}

    current = data.get("current", {})
    unit_symbol = "°F" if units == "fahrenheit" else "°C"
    location = ", ".join(
        part for part in (place.get("name"), place.get("admin1"), place.get("country")) if part
    )

    return {
        "location": location,
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "observed_at": current.get("time"),
        "timezone": data.get("timezone"),
        "temperature": current.get("temperature_2m"),
        "feels_like": current.get("apparent_temperature"),
        "temperature_unit": unit_symbol,
        "conditions": WEATHER_CODES.get(current.get("weather_code"), "unknown"),
        "humidity_percent": current.get("relative_humidity_2m"),
        "precipitation_mm": current.get("precipitation"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "source": "open-meteo.com",
    }


SCHEMA = {
    "name": "get_weather",
    "description": (
        "Get the current weather for a city or place anywhere in the world: "
        "temperature, conditions, humidity and wind. Live data from Open-Meteo."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "City or place name, e.g. 'Chennai' or 'Paris, France'.",
            },
            "units": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "Temperature unit. Defaults to celsius.",
            },
        },
        "required": ["city"],
    },
}
