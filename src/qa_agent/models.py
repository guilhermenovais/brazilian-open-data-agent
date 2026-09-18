"""Pydantic I/O models crossing the qa_agent capability boundary (data-model.md)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AgentAnswer(BaseModel):
    """The `Agent`'s structured `output_type` — the model's own final turn."""

    answer: str = Field(min_length=1)
    outcome: Literal["full", "partial", "none"]


class QuestionAnsweringResult(BaseModel):
    """`answer_question`'s public return type."""

    answer: str
    dataset_key: str
    outcome: Literal["full", "partial", "none"]


class AgentRunLogEntry(BaseModel):
    """FR-013's usage/research record — one per `answer_question` call."""

    question: str
    dataset_key: str
    outcome: Literal["full", "partial", "none"]
    timestamp: datetime
