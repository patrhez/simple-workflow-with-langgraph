# Simple Workflow With LangGraph

This project is a minimal weather app built to show where `LangGraph` differs from plain `LangChain`.

Instead of letting a chain or agent decide everything in one implicit flow, this app makes the workflow explicit:

1. Classify the user's intent with an LLM.
2. Route execution to a graph node based on that intent.
3. Call a real weather tool backed by Open-Meteo only for weather requests.
4. Return a final response from the selected branch.

## Why This Is LangGraph

If you already know LangChain, the key difference in this example is control flow.

- `LangChain` gives you the building blocks: prompts, models, tools, structured output.
- `LangGraph` adds explicit workflow orchestration: state, nodes, edges, and routing.

In this app:

- The intent classifier is a normal LangChain-style LLM call.
- The Open-Meteo weather tool is a normal LangChain tool.
- The router and branch execution are the LangGraph part.

That means you can see and control exactly how the program moves from one step to the next.

## Workflow

```text
START
  |
  v
classify_intent
  |
  +--> weather --> weather_node --> END
  |
  +--> chat ----> chat_node -----> END
  |
  +--> unknown -> unknown_node --> END
```

## Requirements

- Python 3.9+
- `MOONSHOT_API_KEY` set in your environment

This demo uses:

- model: `kimi-k2.5`
- temperature: `1.0`
- base URL: `https://api.moonshot.cn/v1`

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

This project is intended to run inside its local `.venv` only.

## Run

```bash
python3 app.py
```

Example prompts:

- `What's the weather in Shanghai tomorrow?`
- `Will it rain in Beijing?`
- `Hello`
- `Help me write a SQL query`

## File Layout

- `app.py`: thin entrypoint that starts the CLI
- `config.py`: runtime constants and environment lookup
- `models.py`: shared state and structured output schemas
- `logging_utils.py`: logging configuration and decorators
- `llm.py`: Moonshot client setup and LLM exchange logging
- `weather.py`: Open-Meteo integration and weather formatting
- `graph.py`: LangGraph nodes, routing, and graph assembly
- `cli.py`: interactive CLI loop
- `doc/design.md`: design notes and function-by-function explanation
- `pyproject.toml`: project metadata and dependencies

## Notes

- The weather tool resolves the location with Open-Meteo Geocoding and then fetches current plus short-range forecast data from Open-Meteo Forecast.
- The LLM is only used for intent classification and location extraction.
- The routing logic is explicit and deterministic after classification.
- The app logs function inputs, return values, LLM request/response payloads, and Open-Meteo HTTP request/response payloads.
- You can override the default endpoint with `MOONSHOT_BASE_URL`.
- `kimi-k2.5` only accepts temperature `1`, so this project defaults to `1.0`.
