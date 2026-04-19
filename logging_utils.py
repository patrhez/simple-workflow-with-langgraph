from __future__ import annotations

import functools
import json
import logging
from typing import Any

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config import is_logging_enabled


LOGGER = logging.getLogger("weather_app")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO if is_logging_enabled() else logging.WARNING,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    LOGGER.disabled = not is_logging_enabled()


def serialize_for_log(value: Any) -> str:
    if isinstance(value, ChatOpenAI):
        return json.dumps(
            {
                "model": value.model_name,
                "base_url": value.openai_api_base,
                "temperature": value.temperature,
            },
            ensure_ascii=True,
        )
    if isinstance(value, BaseModel):
        return value.model_dump_json()
    if isinstance(value, BaseMessage):
        return json.dumps(
            {
                "type": value.type,
                "content": value.content,
            },
            ensure_ascii=True,
        )
    if isinstance(value, list):
        if value and all(isinstance(item, BaseMessage) for item in value):
            return json.dumps(
                [json.loads(serialize_for_log(item)) for item in value],
                ensure_ascii=True,
            )
        return json.dumps([str(item) for item in value], ensure_ascii=True)
    if isinstance(value, tuple):
        return json.dumps([str(item) for item in value], ensure_ascii=True)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=True, default=str)
    return repr(value)


def log_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        LOGGER.info(
            "CALL %s args=%s kwargs=%s",
            func.__name__,
            serialize_for_log(args),
            serialize_for_log(kwargs),
        )
        try:
            result = func(*args, **kwargs)
            LOGGER.info("RETURN %s -> %s", func.__name__, serialize_for_log(result))
            return result
        except Exception:
            LOGGER.exception("ERROR %s raised an exception", func.__name__)
            raise

    return wrapper


@log_call
def log_http_exchange(
    url: str, params: dict[str, Any], response: dict[str, Any]
) -> dict[str, Any]:
    LOGGER.info("HTTP REQUEST url=%s params=%s", url, serialize_for_log(params))
    LOGGER.info("HTTP RESPONSE url=%s body=%s", url, serialize_for_log(response))
    return response
