from __future__ import annotations

import os


DEFAULT_MODEL = "kimi-k2.5"
DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"
DEFAULT_TEMPERATURE = 1.0
GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_WEATHER_LOCATION = "Beijing"
DEFAULT_LOGGING_ENABLED = False


def get_moonshot_api_key() -> str:
    api_key = os.getenv("MOONSHOT_API_KEY")
    if not api_key:
        raise RuntimeError("MOONSHOT_API_KEY is not set.")
    return api_key


def get_model_name() -> str:
    return os.getenv("MOONSHOT_MODEL", DEFAULT_MODEL)


def get_base_url() -> str:
    return os.getenv("MOONSHOT_BASE_URL", DEFAULT_BASE_URL)


def get_temperature() -> float:
    return float(os.getenv("MOONSHOT_TEMPERATURE", str(DEFAULT_TEMPERATURE)))


def is_logging_enabled() -> bool:
    raw_value = os.getenv("APP_LOGGING", str(DEFAULT_LOGGING_ENABLED)).strip().lower()
    return raw_value in {"1", "true", "yes", "on"}
