from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph

from config import DEFAULT_WEATHER_LOCATION
from llm import build_llm, log_llm_exchange
from logging_utils import LOGGER, log_call
from models import IntentDecision, WorkflowState
from weather import format_weather_error, get_weather


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
    structured_llm = llm.with_structured_output(IntentDecision)
    messages = prompt.invoke({"user_input": state["user_input"]}).to_messages()
    LOGGER.info("LLM TARGET model=%s base_url=%s", llm.model_name, llm.openai_api_base)
    decision = structured_llm.invoke(messages)
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
