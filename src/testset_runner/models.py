"""Pydantic I/O models crossing the testset_runner capability boundary (data-model.md)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from data_access.text_matching import TextMatchingConfig
from qa_agent.models import FailureDetail, RetrievalStep

MatchStatus = Literal["matched", "not_matched", "needs_review", "errored"]
Transition = Literal[
    "newly_passing", "newly_failing", "still_passing", "still_failing", "unchanged_other"
]


class Question(BaseModel):
    """One record of a testset file, field-for-field the bundled schema."""

    n: int = Field(gt=0)
    type: str
    question: str = Field(min_length=1)
    expected: str = Field(min_length=1)
    source: str


class Testset(BaseModel):
    """A loaded, validated testset — identity is `content_hash`, not `path`."""

    path: str
    content_hash: str
    questions: list[Question]


class TargetConfiguration(BaseModel):
    """The model/URL a run targeted. Never carries a credential (Principle VIII)."""

    model_name: str
    base_url: str | None = None


class RetryPolicy(BaseModel):
    """The retry rules for one run, persisted on `TestRun` (006 data-model.md).

    An attempt is one `QuestionAnswerer.answer()` call (`answer_turn()` in a conversation
    run): a full, fresh answer to the question. The provider SDK (e.g. openai,
    `DEFAULT_MAX_RETRIES = 2`) may retry individual HTTP requests inside one attempt, so
    `attempts=1` does not mean exactly one HTTP request (006 research.md §2).

    The wait before retry `k` (k = 1, 2, ...) is
    `min(max(initial_wait_seconds * backoff_multiplier ** (k - 1), retry_after or 0), max_wait_seconds)`,
    where `retry_after` is the failed attempt's provider-suggested wait, if any.
    """

    max_attempts: int = Field(default=3, ge=1)
    """Total attempts per question, including the first. `1` disables retries."""
    initial_wait_seconds: float = Field(default=2.0, ge=0)
    backoff_multiplier: float = Field(default=2.0, ge=1)
    max_wait_seconds: float = Field(default=60.0, ge=0)
    """Upper bound on any single wait, including one suggested by the provider."""


class QuestionResult(BaseModel):
    """The outcome of asking one `Question` within one `TestRun`."""

    n: int
    question: str
    expected: str
    category: str
    actual_answer: str
    agent_outcome: Literal["full", "partial", "none"]
    dataset_key: str
    steps: list[RetrievalStep]
    match_status: MatchStatus
    attempts: int | None = None
    """`1 ≤ attempts ≤ retry_policy.max_attempts`. `None` means not recorded (pre-006 run)."""
    failed_attempts: list[FailureDetail] = []
    """Every failed attempt's `FailureDetail`, in order. Length is `attempts - 1` when the
    question succeeded, and `attempts` when it ended errored."""
    failure: FailureDetail | None = None
    """The final failure when `match_status == "errored"`; `None` for every other question."""


class RunSummary(BaseModel):
    """Derived, never edited independently of the `TestRun.results` it summarizes."""

    total_questions: int
    match_rate: float
    by_status: dict[str, int]
    by_category: dict[str, "RunSummary"]
    target_unreachable: bool
    errored_by_failure_type: dict[str, int] | None = None
    """For errored questions, a count per `failure.type`. Errored results with no recorded
    failure are counted under `"unknown"`. `None` means not recorded (pre-006 run)."""
    retried_questions: int | None = None
    """Count of results with `attempts > 1`. `None` means not recorded."""
    errored_after_retries: int | None = None
    """Count of errored results whose final failure was transient and whose attempts ran
    out (`attempts == max_attempts`). `None` means not recorded."""


class TestRun(BaseModel):
    """One execution of a `Testset` against a `TargetConfiguration`."""

    run_id: str
    created_at: datetime
    testset: Testset
    target: TargetConfiguration
    results: list[QuestionResult]
    summary: RunSummary
    retry_policy: RetryPolicy | None = None
    """The retry policy the run used. `None` means a pre-006 run (not recorded)."""
    text_matching: TextMatchingConfig | None = None
    """The text-matching config the data tools used. `None` means a pre-009 run (not
    recorded). Information only: `compare` never treats a difference as incompatible."""


class ComparisonEntry(BaseModel):
    """One question's outcome across two compared runs, joined by `n`."""

    n: int
    question: str
    status_a: MatchStatus
    status_b: MatchStatus
    transition: Transition


class RunComparison(BaseModel):
    """The result of comparing two `TestRun`s made from the same testset content."""

    run_a: TargetConfiguration
    run_b: TargetConfiguration
    entries: list[ComparisonEntry]
    summary: dict[str, int]
    retry_policy_a: RetryPolicy | None = None
    """Run A's retry policy, or `None` if not recorded. Information only: a policy
    difference never affects transitions."""
    retry_policy_b: RetryPolicy | None = None
