from __future__ import annotations

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from config import (
    DEFAULT_MODEL,
    get_base_url,
    get_model_name,
    get_moonshot_api_key,
    get_temperature,
)
from logging_utils import LOGGER, log_call, serialize_for_log
from models import IntentDecision


@log_call
def build_llm() -> ChatOpenAI:
    api_key = get_moonshot_api_key()
    model = get_model_name()
    temperature = get_temperature()
    if model == DEFAULT_MODEL and temperature != 1.0:
        LOGGER.warning(
            "MODEL CONSTRAINT model=%s overrides unsupported temperature=%s to 1.0",
            model,
            temperature,
        )
        temperature = 1.0

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=get_base_url(),
        temperature=temperature,
    )


@log_call
def log_llm_exchange(
    messages: list[BaseMessage], response: IntentDecision
) -> IntentDecision:
    LOGGER.info("LLM REQUEST messages=%s", serialize_for_log(messages))
    LOGGER.info("LLM RESPONSE parsed=%s", serialize_for_log(response))
    return response
