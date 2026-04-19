from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from langchain_core.tools import tool

from config import DEFAULT_WEATHER_LOCATION, FORECAST_API_URL, GEOCODING_API_URL
from logging_utils import log_call, log_http_exchange


WMO_WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snow fall",
    73: "moderate snow fall",
    75: "heavy snow fall",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


@log_call
def fetch_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    query = urlencode(params, doseq=True)
    request_url = f"{url}?{query}"
    with urlopen(request_url, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return log_http_exchange(url, params, payload)


@log_call
def resolve_location(location: str) -> dict[str, Any]:
    search_term = location.strip() or DEFAULT_WEATHER_LOCATION
    payload = fetch_json(
        GEOCODING_API_URL,
        {
            "name": search_term,
            "count": 1,
            "language": "en",
            "format": "json",
        },
    )
    results = payload.get("results") or []
    if not results:
        raise ValueError(f"No Open-Meteo geocoding result found for location '{search_term}'.")
    return results[0]


@log_call
def fetch_weather_forecast(location_details: dict[str, Any]) -> dict[str, Any]:
    payload = fetch_json(
        FORECAST_API_URL,
        {
            "latitude": location_details["latitude"],
            "longitude": location_details["longitude"],
            "current": [
                "temperature_2m",
                "weather_code",
                "wind_speed_10m",
            ],
            "daily": [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "wind_speed_10m_max",
            ],
            "forecast_days": 2,
            "timezone": location_details.get("timezone", "auto"),
        },
    )
    if "current" not in payload or "daily" not in payload:
        raise ValueError("Open-Meteo forecast response is missing expected current or daily fields.")
    return payload


@log_call
def describe_weather_code(code: int) -> str:
    return WMO_WEATHER_CODES.get(code, f"weather code {code}")


@log_call
def format_location_name(location_details: dict[str, Any]) -> str:
    parts = [
        location_details.get("name"),
        location_details.get("admin1"),
        location_details.get("country"),
    ]
    return ", ".join(part for part in parts if part)


@log_call
def format_weather_report(location_details: dict[str, Any], forecast: dict[str, Any]) -> str:
    current = forecast["current"]
    daily = forecast["daily"]

    current_summary = (
        f"Current weather in {format_location_name(location_details)}: "
        f"{current['temperature_2m']}°C, "
        f"{describe_weather_code(current['weather_code'])}, "
        f"wind {current['wind_speed_10m']} km/h."
    )

    tomorrow_summary = (
        f"Tomorrow ({daily['time'][1]}): "
        f"{describe_weather_code(daily['weather_code'][1])}, "
        f"high {daily['temperature_2m_max'][1]}°C, "
        f"low {daily['temperature_2m_min'][1]}°C, "
        f"precipitation probability up to {daily['precipitation_probability_max'][1]}%, "
        f"wind up to {daily['wind_speed_10m_max'][1]} km/h."
    )

    return f"{current_summary} {tomorrow_summary}"


@tool
@log_call
def get_weather(location: str) -> str:
    """Get real weather conditions and a short forecast from Open-Meteo for a location."""
    resolved_location = resolve_location(location)
    forecast = fetch_weather_forecast(resolved_location)
    return format_weather_report(resolved_location, forecast)
