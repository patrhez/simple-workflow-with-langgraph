from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class WorkflowState(TypedDict, total=False):
    user_input: str
    intent: str
    location: str
    weather_result: str
    final_response: str


class IntentDecision(BaseModel):
    intent: Literal["weather", "chat", "unknown"] = Field(
        description="User intent classification result."
    )
    location: str = Field(
        default="",
        description="Location extracted from the request when intent is weather.",
    )
