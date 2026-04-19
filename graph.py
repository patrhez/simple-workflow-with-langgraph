from __future__ import annotations

import json
import re

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from config import DEFAULT_WEATHER_LOCATION
from llm import build_llm, log_llm_exchange
from logging_utils import LOGGER, log_call
from models import IntentDecision, WorkflowState
from weather import format_weather_error, get_weather


@log_call
def extract_text_content(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(str(part.get("text", "")))
            else:
                text_parts.append(str(part))
        return "\n".join(part for part in text_parts if part).strip()
    return str(content).strip()


@log_call
def parse_intent_from_text(raw_text: str) -> IntentDecision:
    json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if json_match:
        try:
            return IntentDecision.model_validate_json(json_match.group(0))
        except ValidationError:
            LOGGER.warning("Fallback JSON parse failed for classifier response: %s", raw_text)

    intent_match = re.search(
        r"(?:^|\n)\s*(?:intent|意图)\s*[:：]\s*(weather|chat|unknown)\s*(?:$|\n)",
        raw_text,
        re.IGNORECASE,
    )
    location_match = re.search(
        r"(?:^|\n)\s*(?:location|地点|位置)\s*[:：]\s*(.+?)\s*(?:$|\n)",
        raw_text,
        re.IGNORECASE,
    )

    if not intent_match:
        raise ValueError(f"Could not parse classifier response: {raw_text}")

    intent = intent_match.group(1).lower()
    location = location_match.group(1).strip() if location_match else ""
    return IntentDecision(intent=intent, location=location)


@log_call
def invoke_classifier(llm, messages) -> IntentDecision:
    structured_llm = llm.with_structured_output(IntentDecision)
    try:
        return structured_llm.invoke(messages)
    except Exception as exc:
        LOGGER.warning("Structured classifier output failed, falling back to text parsing: %s", exc)
        raw_response = llm.invoke(messages)
        raw_text = extract_text_content(raw_response.content)
        LOGGER.info("LLM FALLBACK RESPONSE raw_text=%s", raw_text)
        return parse_intent_from_text(raw_text)


@log_call
def classify_intent(state: WorkflowState) -> WorkflowState:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You classify the user's intent for a simple weather application. "
                "Return exactly one JSON object and nothing else. "
                "Do not include markdown, labels, commentary, or extra text. "
                "The JSON must match this shape exactly: "
                '{{"intent":"weather|chat|unknown","location":"string"}}. '
                "Rules: "
                "Use 'weather' when the user asks about weather or forecast. "
                "Use 'chat' for greetings or general conversation. "
                "Use 'unknown' for everything else. "
                "Extract the location only when it is clearly present. "
                "If no location is present, return an empty string for location. "
                "Valid intent values are only: weather, chat, unknown. "
                'Example valid output: {{"intent":"weather","location":"Shenzhen"}}.',
            ),
            ("human", "{user_input}"),
        ]
    )

    llm = build_llm()
    messages = prompt.invoke({"user_input": state["user_input"]}).to_messages()
    LOGGER.info("LLM TARGET model=%s base_url=%s", llm.model_name, llm.openai_api_base)
    decision = invoke_classifier(llm, messages)
    log_llm_exchange(messages, decision)
    return {
        "intent": decision.intent,
        "location": decision.location.strip(),
    }


@log_call
def route_intent(state: WorkflowState) -> str:
    intent = state.get("intent", "unknown")
    if intent == "weather":
        return "weather"
    if intent == "chat":
        return "chat"
    return "unknown"


@log_call
def weather_node(state: WorkflowState) -> WorkflowState:
    location = state.get("location") or DEFAULT_WEATHER_LOCATION
    try:
        forecast = get_weather.invoke({"location": location})
    except Exception:
        forecast = format_weather_error(location)
    return {
        "weather_result": forecast,
        "final_response": forecast,
    }


@log_call
def chat_node(state: WorkflowState) -> WorkflowState:
    return {
        "final_response": (
            "This demo only handles weather requests. "
            "Try asking something like: What's the weather in Shanghai tomorrow?"
        )
    }


@log_call
def unknown_node(state: WorkflowState) -> WorkflowState:
    return {
        "final_response": (
            "I could not map that request to this workflow. "
            "This graph currently supports weather intent routing only."
        )
    }


@log_call
def build_graph():
    graph = StateGraph(WorkflowState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("weather_node", weather_node)
    graph.add_node("chat_node", chat_node)
    graph.add_node("unknown_node", unknown_node)

    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_intent,
        {
            "weather": "weather_node",
            "chat": "chat_node",
            "unknown": "unknown_node",
        },
    )
    graph.add_edge("weather_node", END)
    graph.add_edge("chat_node", END)
    graph.add_edge("unknown_node", END)

    return graph.compile()
