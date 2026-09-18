"""Pydantic I/O models crossing the testset_runner capability boundary (data-model.md)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from qa_agent.models import RetrievalStep

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


class RunSummary(BaseModel):
    """Derived, never edited independently of the `TestRun.results` it summarizes."""

    total_questions: int
    match_rate: float
    by_status: dict[str, int]
    by_category: dict[str, "RunSummary"]
    target_unreachable: bool


class TestRun(BaseModel):
    """One execution of a `Testset` against a `TargetConfiguration`."""

    run_id: str
    created_at: datetime
    testset: Testset
    target: TargetConfiguration
    results: list[QuestionResult]
    summary: RunSummary


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
