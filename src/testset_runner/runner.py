"""run_testset: the one public entry point for User Story 1 (contracts/running.md)."""

import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from data_access.text_matching import TextMatchingConfig
from qa_agent.answerer import QuestionAnswerer
from qa_agent.models import FailureDetail, QuestionAnsweringResult
from testset_runner.loader import TestsetLoader
from testset_runner.matcher import DeterministicMatcher, MatchStrategy, NumericMatchStrategy
from testset_runner.models import (
    QuestionResult,
    RetryPolicy,
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

# The `errored_by_failure_type` bucket for an errored result whose answerer supplied no
# `FailureDetail` (e.g. a third-party or test `QuestionAnswerer`).
_UNKNOWN_FAILURE_TYPE = "unknown"


def run_testset(
    testset_path: str | Path,
    target: TargetConfiguration,
    *,
    answerer: QuestionAnswerer,
    matcher: MatchStrategy = NumericMatchStrategy(),
    store: RunStore,
    retry_policy: RetryPolicy = RetryPolicy(),
    text_matching: TextMatchingConfig | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> TestRun:
    """Asks every question of the testset, grades the answers, and saves one `TestRun`.

    Each question is asked up to `retry_policy.max_attempts` times while its failure is
    transient, waiting `_wait(...)` between attempts (006 contracts/running-with-retry.md).
    Every attempt is a brand-new `answerer.answer()` call: nothing from a failed attempt,
    or from another question, is ever passed back in, so per-question isolation holds
    for attempts too. Only the bookkeeping (`attempts`, `failed_attempts`) is carried
    between attempts, and the recorded result is always the last attempt's.

    `text_matching` is recorded on the run as given (the answerer's own config; `None`
    when the caller does not know it).

    `sleep` is a test seam so the wait sequence can be asserted without real waiting. A
    `KeyboardInterrupt` during a wait propagates out before `store.save`, so no partial
    run is ever persisted.
    """
    testset = TestsetLoader().load(testset_path)
    grader = DeterministicMatcher(matcher)

    results: list[QuestionResult] = []
    for question in testset.questions:
        answer_result, attempts, failed_attempts = _ask_with_retry(
            lambda: answerer.answer(question.question), retry_policy, sleep
        )
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
                attempts=attempts,
                failed_attempts=failed_attempts,
                failure=answer_result.failure if answer_result.errored else None,
            )
        )

    summary = _summarize(results, max_attempts=retry_policy.max_attempts)
    run = TestRun(
        run_id=datetime.now(timezone.utc).strftime(_RUN_ID_FORMAT),
        created_at=datetime.now(timezone.utc),
        testset=testset,
        target=target,
        results=results,
        summary=summary,
        retry_policy=retry_policy,
        text_matching=text_matching,
    )
    store.save(run)
    return run


def _ask_with_retry(
    ask: Callable[[], QuestionAnsweringResult],
    policy: RetryPolicy,
    sleep: Callable[[float], None],
) -> tuple[QuestionAnsweringResult, int, list[FailureDetail]]:
    """Returns the last attempt's result, the number of attempts, and every failure seen.

    `ask` makes one fresh attempt. It is a callable rather than an answerer + question so
    the standalone runner (`answerer.answer(question)`) and the conversation runner
    (`answerer.answer_turn(message, context)`) share one retry loop.

    An errored result with no `failure` (a legacy/third-party answerer) is treated as a
    non-transient failure with no details.
    """
    failed_attempts: list[FailureDetail] = []
    attempts = 0
    while True:
        attempts += 1
        result = ask()
        if not result.errored:
            return result, attempts, failed_attempts
        failure = result.failure
        if failure is not None:
            failed_attempts.append(failure)
        if failure is None or not failure.transient or attempts >= policy.max_attempts:
            return result, attempts, failed_attempts
        sleep(_wait(policy, attempts, failure.retry_after_seconds))


def _wait(policy: RetryPolicy, k: int, retry_after: float | None) -> float:
    """The wait before retry `k` (k ≥ 1): increasing backoff, raised by the provider's
    suggestion but never shortened by it, and capped at `max_wait_seconds`."""
    backoff = policy.initial_wait_seconds * policy.backoff_multiplier ** (k - 1)
    return min(max(backoff, retry_after or 0.0), policy.max_wait_seconds)


def _summarize(results: list[QuestionResult], *, max_attempts: int) -> RunSummary:
    by_category: dict[str, RunSummary] = {}
    for category in sorted({r.category for r in results}):
        cat_results = [r for r in results if r.category == category]
        by_category[category] = _tally(
            cat_results, by_category={}, target_unreachable=False, max_attempts=max_attempts
        )

    eligible = [r for r in results if r.dataset_key != _UNKNOWN_DATASET_KEY]
    target_unreachable = bool(eligible) and all(r.match_status == "errored" for r in eligible)

    return _tally(
        results,
        by_category=by_category,
        target_unreachable=target_unreachable,
        max_attempts=max_attempts,
    )


def _tally(
    results: list[QuestionResult],
    *,
    by_category: dict[str, RunSummary],
    target_unreachable: bool,
    max_attempts: int,
) -> RunSummary:
    total = len(results)
    by_status: dict[str, int] = {}
    for r in results:
        by_status[r.match_status] = by_status.get(r.match_status, 0) + 1
    errored_by_failure_type: dict[str, int] = {}
    for r in results:
        if r.match_status == "errored":
            key = r.failure.type if r.failure else _UNKNOWN_FAILURE_TYPE
            errored_by_failure_type[key] = errored_by_failure_type.get(key, 0) + 1
    retried_questions = sum(1 for r in results if (r.attempts or 0) > 1)
    errored_after_retries = sum(
        1
        for r in results
        if r.match_status == "errored"
        and r.failure is not None
        and r.failure.transient
        and r.attempts == max_attempts
    )
    matched = by_status.get("matched", 0)
    match_rate = matched / total if total else 0.0
    return RunSummary(
        total_questions=total,
        match_rate=match_rate,
        by_status=by_status,
        by_category=by_category,
        target_unreachable=target_unreachable,
        errored_by_failure_type=errored_by_failure_type,
        retried_questions=retried_questions,
        errored_after_retries=errored_after_retries,
    )
