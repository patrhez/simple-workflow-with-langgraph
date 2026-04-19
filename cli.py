from __future__ import annotations

from dotenv import load_dotenv

from graph import build_graph
from logging_utils import configure_logging, log_call


@log_call
def main() -> None:
    configure_logging()
    load_dotenv()
    graph = build_graph()

    print("Simple LangGraph Weather App")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break

        result = graph.invoke({"user_input": user_input})
        print(f"Assistant: {result['final_response']}\n")
