"""run_testset: the one public entry point for User Story 1 (contracts/running.md)."""

from datetime import datetime, timezone
from pathlib import Path

from qa_agent.answerer import QuestionAnswerer
from testset_runner.loader import TestsetLoader
from testset_runner.matcher import DeterministicMatcher, MatchStrategy, NumericMatchStrategy
from testset_runner.models import (
    QuestionResult,
    RunSummary,
    TargetConfiguration,
    TestRun,
)
from testset_runner.store import RunStore

_RUN_ID_FORMAT = "%Y%m%dT%H%M%S%fZ"

# Mirrors qa_agent.capabilities._UNKNOWN_DATASET_KEY — the fixed sentinel set on a
# QuestionResult when dataset selection itself failed, i.e. the question never
# reached the model/target at all (research.md §6). Duplicated here, not imported,
# since it is qa_agent's own private implementation detail.
_UNKNOWN_DATASET_KEY = "<none>"


def run_testset(
    testset_path: str | Path,
    target: TargetConfiguration,
    *,
    answerer: QuestionAnswerer,
    matcher: MatchStrategy = NumericMatchStrategy(),
    store: RunStore,
) -> TestRun:
    testset = TestsetLoader().load(testset_path)
    grader = DeterministicMatcher(matcher)

    results: list[QuestionResult] = []
    for question in testset.questions:
        answer_result = answerer.answer(question.question)
        if answer_result.errored:
            match_status = "errored"
        else:
            match_status = grader.grade(question.expected, answer_result.answer)
        results.append(
            QuestionResult(
                n=question.n,
                question=question.question,
                expected=question.expected,
                category=question.type,
                actual_answer=answer_result.answer,
                agent_outcome=answer_result.outcome,
                dataset_key=answer_result.dataset_key,
                steps=answer_result.steps,
                match_status=match_status,
            )
        )

    summary = _summarize(results)
    run = TestRun(
        run_id=datetime.now(timezone.utc).strftime(_RUN_ID_FORMAT),
        created_at=datetime.now(timezone.utc),
        testset=testset,
        target=target,
        results=results,
        summary=summary,
    )
    store.save(run)
    return run


def _summarize(results: list[QuestionResult]) -> RunSummary:
    by_category: dict[str, RunSummary] = {}
    for category in sorted({r.category for r in results}):
        cat_results = [r for r in results if r.category == category]
        by_category[category] = _tally(cat_results, by_category={}, target_unreachable=False)

    eligible = [r for r in results if r.dataset_key != _UNKNOWN_DATASET_KEY]
    target_unreachable = bool(eligible) and all(r.match_status == "errored" for r in eligible)

    return _tally(results, by_category=by_category, target_unreachable=target_unreachable)


def _tally(
    results: list[QuestionResult], *, by_category: dict[str, RunSummary], target_unreachable: bool
) -> RunSummary:
    total = len(results)
    by_status: dict[str, int] = {}
    for r in results:
        by_status[r.match_status] = by_status.get(r.match_status, 0) + 1
    matched = by_status.get("matched", 0)
    match_rate = matched / total if total else 0.0
    return RunSummary(
        total_questions=total,
        match_rate=match_rate,
        by_status=by_status,
        by_category=by_category,
        target_unreachable=target_unreachable,
    )
