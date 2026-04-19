# Design Documentation

## Purpose

This project is a minimal LangGraph example for learning how graph-based orchestration differs from plain LangChain usage.

The application handles one core business capability:

- classify user intent
- route execution through an explicit graph
- call a real weather tool for weather requests

The code is intentionally small, but it is now split into focused modules so each responsibility is easier to inspect.

## Module Layout

- `app.py`: thin top-level entrypoint that calls the CLI main function
- `config.py`: constants and environment variable access
- `models.py`: `WorkflowState` and `IntentDecision`
- `logging_utils.py`: logging setup, serialization helpers, and decorators
- `llm.py`: Moonshot LLM construction and LLM request/response logging
- `weather.py`: Open-Meteo geocoding, forecast retrieval, and formatting
- `graph.py`: graph nodes, router, and compiled graph builder
- `cli.py`: interactive terminal loop

## High-Level Design

The runtime flow is:

1. `main()` loads environment variables, configures logging, builds the graph, and starts a CLI loop.
2. `build_graph()` defines the LangGraph state machine.
3. `classify_intent()` calls the LLM to classify the request and extract a location.
4. `route_intent()` chooses the next node based on the classified intent.
5. One of the terminal nodes runs:
   - `weather_node()`
   - `chat_node()`
   - `unknown_node()`

This separates decision-making from execution. The classifier only decides intent. The router only chooses a branch. The execution node only performs its branch-specific work.

## Why LangGraph Here

This example uses both LangChain and LangGraph, but they serve different roles.

- LangChain provides the LLM wrapper, prompt template, tool abstraction, and structured output parsing.
- LangGraph provides the explicit workflow graph, state passing, and conditional routing.

If this were written only as a simple LangChain chain, the branching would likely be hidden inside imperative Python or agent behavior. With LangGraph, the branching is modeled directly as nodes and edges.

## State Model

### `WorkflowState`

`WorkflowState` is a `TypedDict` that defines the shared state flowing through the graph.

Fields:

- `user_input`: raw text entered by the user
- `intent`: the classifier result
- `location`: the extracted location for weather requests
- `weather_result`: the real forecast result returned by the weather tool
- `final_response`: the final text shown to the user

This state object is the contract between graph nodes.

### `IntentDecision`

`IntentDecision` is a Pydantic model used as the structured output schema for the LLM classification step.

Fields:

- `intent`: one of `weather`, `chat`, or `unknown`
- `location`: extracted location text, if any

This ensures the LLM output is parsed into a predictable shape before the router uses it.

## Logging Design

The application logs function calls and returns so execution is easy to trace.

### `configure_logging()`

Initializes the logger format and level for the CLI app.

### `serialize_for_log(value)`

Converts runtime values into log-friendly text.

It handles:

- Pydantic models
- LangChain message objects
- lists and dictionaries
- plain Python values

### `log_call(func)`

A decorator that prints:

- function name
- input positional arguments
- input keyword arguments
- return value

This is applied to the main workflow functions so you can see what each step receives and produces.

### `log_llm_exchange(messages, response)`

Logs the LLM request and response explicitly.

It prints:

- the final prompt messages sent to the model
- the parsed structured result returned by the model

This is separate from `log_call()` because LLM interaction is important enough to log in a dedicated format.

## Function-by-Function Reference

### `get_weather(location)`

Real weather tool function.

Responsibilities:

- accept a location string
- resolve the location through Open-Meteo Geocoding
- fetch current and forecast data through Open-Meteo Forecast
- return a formatted weather summary string

This function is still small, but now it represents a real integration boundary instead of a mock.

### `fetch_json(url, params)`

Shared HTTP helper.

Responsibilities:

- build the query string
- call the remote Open-Meteo endpoint
- parse the JSON response
- log the HTTP request and response

### `resolve_location(location)`

Geocoding helper.

Responsibilities:

- call the Open-Meteo geocoding endpoint
- turn a free-form place name into coordinates and timezone metadata
- return the best matching location result

### `fetch_weather_forecast(location_details)`

Forecast helper.

Responsibilities:

- call the Open-Meteo forecast endpoint using the resolved coordinates
- request both current weather and daily forecast fields
- validate that the expected payload fields exist

### `describe_weather_code(code)`

Maps Open-Meteo weather codes into readable text.

### `format_location_name(location_details)`

Builds a readable place label from the geocoding result.

### `format_weather_report(location_details, forecast)`

Builds the user-facing weather summary from the Open-Meteo response.

### `build_llm()`

Creates the `ChatOpenAI` client configured for Moonshot.

Responsibilities:

- read `MOONSHOT_API_KEY`
- set the default model to `kimi-k2.5`
- set the default temperature to `1.0`
- use the Moonshot OpenAI-compatible base URL

This function centralizes model configuration so the rest of the workflow does not need to know connection details.

### `classify_intent(state)`

Runs the LLM classification step.

Responsibilities:

- build the classification prompt
- create the structured-output LLM wrapper
- render the prompt into messages
- log the target model and request/response payload
- return the normalized graph state update

This function is the only place in the graph that depends on the LLM.

### `route_intent(state)`

Pure routing function.

Responsibilities:

- inspect `state["intent"]`
- map that value to the next graph edge

This function contains no LLM logic and no side effects.

### `weather_node(state)`

Weather execution node.

Responsibilities:

- choose a default location when none is extracted
- call the real Open-Meteo weather tool
- write the tool result into graph state

### `chat_node(state)`

Fallback node for greeting or small-talk style requests.

Responsibilities:

- return a message explaining that this demo is focused on weather

### `unknown_node(state)`

Fallback node for unsupported requests.

Responsibilities:

- return a message explaining the current graph scope

### `build_graph()`

Constructs and compiles the LangGraph state machine.

Responsibilities:

- register nodes
- connect the start edge
- register conditional routing from the classifier
- connect terminal nodes to `END`

This function is the core place where the workflow topology is defined.

### `main()`

CLI entry point.

Responsibilities:

- configure logging
- load environment variables
- compile the graph
- read user input in a loop
- invoke the graph and print the final response

## Execution Trace Example

For a request like:

`What's the weather in Shanghai tomorrow?`

the expected path is:

1. `main()`
2. `build_graph()`
3. `classify_intent()`
4. `route_intent()` returns `weather`
5. `weather_node()`
6. `get_weather()`

The logs show each transition with inputs and outputs, which makes it easier to learn how LangGraph moves state between nodes.

## Environment Variables

- `MOONSHOT_API_KEY`: required
- `MOONSHOT_MODEL`: optional, defaults to `kimi-k2.5`
- `MOONSHOT_BASE_URL`: optional, defaults to `https://api.moonshot.cn/v1`
- `MOONSHOT_TEMPERATURE`: optional, defaults to `1.0`

## External APIs

This project uses two Open-Meteo endpoints:

- Geocoding API: turns a place name into latitude, longitude, and timezone
- Forecast API: returns current weather plus daily forecast values for those coordinates

This combination is the right fit for the app because the workflow starts with a human-readable location name, while the forecast endpoint requires coordinates.

## Design Tradeoffs

- A modular package layout keeps related logic together without hiding the workflow shape.
- Open-Meteo keeps the weather integration simple because it does not require an API key for this use case.
- Structured output keeps the classifier result reliable.
- Explicit routing keeps LangGraph’s role visible.
- Decorator-based logging avoids repetitive print statements in every function body.
