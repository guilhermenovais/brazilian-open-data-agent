# Contract: Failure Translation

Two independent failure surfaces exist in this feature: whole-run/whole-comparison failures
(raised, per `running.md`/`comparing.md`), and single-question failures (never raised — folded
into that question's own `match_status="errored"`, per `qa_agent`'s own unchanged "never
raises" contract).

## Whole-run / whole-comparison exceptions

| Exception             | Raised by                          | Raised to        | User-facing effect |
|------------------------|-------------------------------------|-------------------|----------------------|
| `TestsetLoadError`      | `TestsetLoader.load`                 | `run_testset`, before any question is asked | The CLI prints a clear, specific reason (file missing / unreadable / a named record missing `question`/`expected` / duplicate `n`) and exits non-zero — no run file is written, no misleading partial report exists (FR-013). |
| `RunLoadError`           | `RunStore.load`                       | `compare_runs`, before either run is used     | The CLI prints which of the two paths failed to load and why, and exits non-zero. |
| `IncompatibleRunsError`   | `compare_runs` itself (content-hash check) | `compare_runs`'s caller                         | The CLI states plainly that the two runs used different testset content (not just a generic error) and does not print any per-question diff (FR-011, Edge Cases). |

All three are subclasses of `TestsetRunnerError` (exceptions.py), mirroring
`dataset_selector.exceptions`'/`data_access.exceptions`'s own per-package base-exception
pattern.

## Single-question failure: `errored`, not an exception

A question-level failure — the underlying `qa_agent.capabilities.answer_question` call
returning `errored=True` (data-model.md) — is **not** raised as an exception anywhere in
`testset_runner`. It is recorded as `QuestionResult.match_status="errored"` and the run
continues (FR-004). This is a deliberate continuation of `003`'s own design (`answer_question`
never raises to its caller); `testset_runner` adds no new exception type for this case because
one already isn't needed — the information travels as data (`errored: bool` →
`match_status: "errored"`), exactly the way `qa_agent`'s own outcome/answer already do.

## Design note: why `target_unreachable` is a `RunSummary` field, not an exception

A whole-run connectivity failure (Edge Cases: "the configured model/URL is unreachable for the
entire run") is detected only *after* every question has already been attempted and recorded
(research.md §6) — by definition, it cannot be raised partway through without contradicting
FR-004's "every other question is still asked" guarantee. It is surfaced as
`RunSummary.target_unreachable=True`, read by the CLI to print a leading warning instead of a
misleading match rate, rather than as an exception that would abort the run and discard the 50
already-produced (if uniformly errored) `QuestionResult`s.
