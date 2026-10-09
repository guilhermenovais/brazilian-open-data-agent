"""Pydantic I/O models crossing the qa_agent capability boundary (data-model.md)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# The agent's own classification of its answer (008 data-model.md):
#   full                — answered in full from queried data;
#   partial             — part answered, the rest declared as not covered;
#   none                — nothing answered: not covered, no match, or a processing failure;
#   needs_clarification — several readings with different amounts; the answer is a
#                         clarifying question with no dataset values.
Outcome = Literal["full", "partial", "none", "needs_clarification"]


class AgentAnswer(BaseModel):
    """The `Agent`'s structured `output_type` — the model's own final turn."""

    answer: str = Field(min_length=1)
    outcome: Outcome = Field(
        description=(
            "Classificação do próprio resultado. "
            "full: a pergunta foi totalmente respondida com dados consultados; "
            "partial: parte da pergunta foi respondida e o que falta foi declarado; "
            "none: não foi possível responder (dados não cobrem a pergunta ou nada corresponde); "
            "needs_clarification: a pergunta tem mais de uma leitura com valores diferentes; "
            "a resposta é uma pergunta de esclarecimento sem valores."
        )
    )


class RetrievalStep(BaseModel):
    """One tool call/return pair pulled from a run's `all_messages()` (data-model.md)."""

    tool_name: str
    arguments: dict
    result_summary: str


class FailureDetail(BaseModel):
    """Describes one failure: why a question errored (006 data-model.md).

    Built only by `qa_agent.failures.describe_failure` / the dataset-selection branch of
    `answer_question`; persisted in run files and the run log.
    """

    type: str = Field(min_length=1)
    """Class name of the **root** exception in the cause chain."""
    message: str
    """`str(root)`, credential-free and length-capped. May be `""`, and is never replaced
    with a placeholder."""
    transient: bool
    """`True` only if a transient rule matches some link of the chain. Always `False` for
    dataset-selection failures and for anything unrecognized."""
    retry_after_seconds: float | None = None
    """Provider-suggested wait. Stored exactly as the provider gave it. The cap is applied
    only when waiting."""


class QuestionAnsweringResult(BaseModel):
    """`answer_question`'s public return type."""

    answer: str
    dataset_key: str
    outcome: Outcome
    steps: list[RetrievalStep] = []
    errored: bool = False
    failure: FailureDetail | None = None
    briefing_fingerprint: str | None = Field(
        default=None,
        description=(
            "SHA-256 hex of the dataset briefing used; None when dataset selection failed"
        ),
    )


class ConversationLogContext(BaseModel):
    """Where a conversational turn sits in its chat, and how its history was trimmed
    (008 data-model.md). Only `answer_turn` builds one."""

    conversation_id: str
    turn_index: int = Field(ge=1)
    history_turns_used: int = Field(ge=0)
    """Turns passed to the model after `fit_history`."""
    history_turns_dropped: int = Field(ge=0)
    """`len(context.history) - history_turns_used`."""
    history_char_limit: int = Field(ge=0)
    """The limit in force for this turn."""
    prompt_version: str
    """The system prompt version used, e.g. `"v3"`."""


class AgentRunLogEntry(BaseModel):
    """FR-013's usage/research record — one per `answer_question` or `answer_turn` call.

    `question` is the current message exactly as typed; for a conversation turn it is
    never a rewritten, context-filled question.
    """

    question: str
    dataset_key: str
    outcome: Outcome
    timestamp: datetime
    failure: FailureDetail | None = None
    conversation: ConversationLogContext | None = None
    """Set by `answer_turn`; `None` for `answer_question` and for log lines written
    before 008."""
