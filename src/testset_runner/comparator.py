"""compare_runs: the one public entry point for User Story 2 (contracts/comparing.md)."""

from pathlib import Path

from testset_runner.exceptions import IncompatibleRunsError
from testset_runner.models import ComparisonEntry, MatchStatus, RunComparison, Transition
from testset_runner.store import RunStore

_MATCHED: MatchStatus = "matched"
_REVIEW_LIKE = {"needs_review", "errored"}


def compare_runs(
    run_a_path: str | Path,
    run_b_path: str | Path,
    *,
    store: RunStore,
) -> RunComparison:
    run_a = store.load(run_a_path)
    run_b = store.load(run_b_path)

    if run_a.testset.content_hash != run_b.testset.content_hash:
        raise IncompatibleRunsError(
            "The two runs were made from different testset content "
            f"({run_a.testset.path} vs {run_b.testset.path})."
        )

    results_b_by_n = {r.n: r for r in run_b.results}
    entries: list[ComparisonEntry] = []
    for result_a in run_a.results:
        result_b = results_b_by_n[result_a.n]
        entries.append(
            ComparisonEntry(
                n=result_a.n,
                question=result_a.question,
                status_a=result_a.match_status,
                status_b=result_b.match_status,
                transition=_transition(result_a.match_status, result_b.match_status),
            )
        )

    summary: dict[str, int] = {}
    for entry in entries:
        summary[entry.transition] = summary.get(entry.transition, 0) + 1

    return RunComparison(run_a=run_a.target, run_b=run_b.target, entries=entries, summary=summary)


def _transition(status_a: MatchStatus, status_b: MatchStatus) -> Transition:
    if status_a == _MATCHED and status_b == _MATCHED:
        return "still_passing"
    if status_a != _MATCHED and status_b == _MATCHED:
        return "newly_passing"
    if status_a == _MATCHED and status_b != _MATCHED:
        return "newly_failing"
    if status_a == status_b and status_a in _REVIEW_LIKE:
        return "unchanged_other"
    return "still_failing"
