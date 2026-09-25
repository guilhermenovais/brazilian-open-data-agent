"""Pydantic models for scripted conversations and conversation runs (008 data-model.md).

Kept apart from `models.py` so the standalone `run` path's models stay exactly as they are
(FR-014). Shared building blocks (`RetrievalStep`, `FailureDetail`, `TargetConfiguration`,
`RetryPolicy`) are reused, not copied.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from qa_agent.models import FailureDetail, RetrievalStep
from testset_runner.models import RetryPolicy, TargetConfiguration

TurnStatus = Literal["matched", "not_matched", "needs_review", "errored", "unscored"]
Outcome = Literal["full", "partial", "none"]


class ScriptedTurn(BaseModel):
    """One user message of a scripted conversation, with what its answer should be."""

    message: str = Field(min_length=1)
    expected: str | None = None
    """Same grammar as `Question.expected`: a number, `~` prefix for ±1%. A non-numeric
    value is always `needs_review`."""
    expected_outcome: Outcome | None = None
    """Compared exactly with the agent's own outcome."""
    source: str | None = None
    """Where the expected value came from, e.g. `dados_gerais/tb_geral.csv`."""
    scored: bool | None = None
    """`None` means scored iff `expected` or `expected_outcome` is set. `false` forces a
    context-only turn. `true` without either expectation is a load error."""

    @property
    def has_expectation(self) -> bool:
        return self.expected is not None or self.expected_outcome is not None

    @property
    def is_scored(self) -> bool:
        if self.scored is None:
            return self.has_expectation
        return self.scored


class ScriptedConversation(BaseModel):
    """One conversation of the test set, replayed turn by turn from an empty history."""

    id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    description: str = ""
    turns: list[ScriptedTurn] = Field(min_length=1)


class ConversationTestset(BaseModel):
    """A loaded, validated conversation test set. Identity is `content_hash`, not `path`."""

    path: str
    content_hash: str
    conversations: list[ScriptedConversation]


class TurnResult(BaseModel):
    """The outcome of one scripted turn within one `ConversationRun`."""

    turn_index: int = Field(ge=1)
    message: str
    expected: str | None = None
    expected_outcome: Outcome | None = None
    actual_answer: str
    agent_outcome: Outcome
    dataset_key: str
    steps: list[RetrievalStep]
    """Current turn only."""
    history_turns_sent: int = Field(ge=0)
    """Turns passed in `ConversationContext.history`, before trimming."""
    history_turns_used: int = Field(ge=0)
    """`len(fit_history(history, run.history_char_limit))`: the turns the model actually
    received. Lets FR-011 / SC-006 be checked from the run file alone."""
    scored: bool
    """Whether this turn counts toward the match rate (`ScriptedTurn.is_scored`). Recorded
    so an errored context turn, whose status is `errored` rather than `unscored`, still
    stays out of the rate it does not measure."""
    status: TurnStatus
    ungrounded_figures: list[str] = []
    """Figures in the answer found in neither the message nor this turn's retrievals.
    Reported, not scored (SC-003)."""
    attempts: int = Field(ge=1)
    failed_attempts: list[FailureDetail] = []
    failure: FailureDetail | None = None
    """Set only when `status == "errored"`."""


class ConversationResult(BaseModel):
    conversation_id: str
    """The scripted conversation's `id`."""
    category: str
    turns: list[TurnResult]


class ConversationRunSummary(BaseModel):
    """Derived, never edited independently of the results it summarizes."""

    total_conversations: int
    total_turns: int
    scored_turns: int
    """Turns with `scored == True`, errored ones included. Context turns never count, even
    when they error, so a category's rate reads directly as its criterion."""
    match_rate: float
    """`matched / scored_turns`, or 0.0 when nothing is scored."""
    by_status: dict[str, int]
    by_category: dict[str, "ConversationRunSummary"]
    turns_with_ungrounded_figures: int
    target_unreachable: bool
    """Every turn that reached the model errored (same rule as `RunSummary`)."""


class ConversationRun(BaseModel):
    """One execution of a `ConversationTestset` against a `TargetConfiguration`."""

    run_id: str
    created_at: datetime
    testset: ConversationTestset
    target: TargetConfiguration
    retry_policy: RetryPolicy
    history_char_limit: int = Field(ge=0)
    prompt_version: str
    results: list[ConversationResult]
    summary: ConversationRunSummary
