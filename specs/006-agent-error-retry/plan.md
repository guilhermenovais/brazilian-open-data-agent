# Implementation Plan: Agent Error Details and Bounded Retry

**Branch**: `006-agent-error-retry` | **Date**: 2026-09-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-agent-error-retry/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Two changes affect the testset runner's evaluation reports:

1. **Failure details.** Every failure caught by `qa_agent.answer_question` now becomes a
   `FailureDetail`. That covers dataset-selection failures and exceptions from
   `agent.run_sync`. A `FailureDetail` records the root-cause type, a message with credentials
   removed and a length cap, and a transient/non-transient verdict. It travels on
   `QuestionAnsweringResult`, into the run log, and into each `QuestionResult`. Run summaries
   gain per-failure-type counts.
2. **Bounded retry.** `testset_runner.run_testset` re-asks a question with a fresh
   `answerer.answer()` call when the failure is transient. It waits with increasing,
   `Retry-After`-aware, capped delays, up to `RetryPolicy.max_attempts` (default 3, set with
   `--max-attempts`). Every attempt's failure is recorded, and the policy is persisted with the
   run and shown in comparisons.

The retry loop sits *above* the existing `QuestionAnswerer` seam. Per-question isolation is
therefore inherited unchanged, and the chat web UI's behavior does not change (research.md §1).
All persisted-model changes are additive and optional, so older run files still load
(research.md §9).

## Technical Context

**Language/Version**: Python 3.11+ (venv currently 3.12)

**Primary Dependencies**: `pydantic-ai` 2.45.0. Its provider-neutral exceptions
(`ModelHTTPError` with `status_code` and `retry_after`, and `ModelAPIError`) are the only
framework types the classifier inspects (research.md §3). Also `pydantic` v2 and
`pydantic-settings`, both already present. No new dependency. `tenacity` is installed
transitively but deliberately not used (research.md §1).

**Storage**: No new files or paths. The existing `data/testset_runs/<run_id>.json` gains
optional fields, and `data/logs/qa_agent_runs.jsonl` entries gain an optional `failure`.

**Testing**: pytest + pyright (existing CI). `FunctionModel`-driven contract tests raise real
`pydantic_ai.exceptions` instances. Fake answerers with scripted failure sequences plus a fake
`sleep` cover the runner. A pre-feature run fixture checks backward compatibility
(research.md §11).

**Target Platform**: Linux, local CLI process (`python -m testset_runner.cli`).

**Project Type**: Single-project Python library + CLI (`src/` layout).

**Performance Goals**: None beyond bounded run duration. With the defaults, a fully unreachable
target adds at most 6 s of question-level waiting per question, or ≤ 120 s per question when
the provider sends `Retry-After` (SC-005, research.md §7).

**Constraints**: No credential in any persisted run or log (FR-005/SC-004). Per-question and
per-attempt isolation (FR-015). The chat answer text is unchanged (FR-009). Pre-feature runs
still load and compare (FR-024). `testset_runner` never imports `pydantic_ai`.

**Scale/Scope**: Two new small `qa_agent` modules (`failures.py`, `transient.py`). Additive
model changes in `qa_agent/models.py` and `testset_runner/models.py`. A retry loop and summary
extensions in `runner.py`. Comparator/CLI additions. No change to `data_access`,
`dataset_selector` or `web_ui`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| I. Reproducibility | The retry policy, including wait parameters, is persisted per run (FR-022) and shown in comparisons (FR-023). Each attempt's failures are recorded (FR-018), so a run's match rate can be explained from the run file alone. Retry waits are deterministic, with no jitter (research.md §7). The one unrecorded retry layer (OpenAI SDK request retries) is documented explicitly (research.md §2). **Pass.** |
| II. Evidence Before Implementation | Motivated by an observed gap: errored questions today carry no cause (`capabilities.py` `except Exception:` discards it). Each classification rule was checked against the installed `pydantic-ai`/`openai` source, not assumed (research.md §2–§4). **Pass.** |
| III. Documentation Is a Deliverable | research.md / data-model.md / contracts / quickstart.md are produced. Module docstrings for `failures.py`/`transient.py` and the `RetryPolicy` docstring (including the SDK-retry note) are carried into tasks. **Pass**, carried into tasks. |
| IV. Tests Document Behavior | Contract tests map 1:1 to US1–US3 acceptance scenarios and SC-002/003/004/006 (quickstart.md table). The classification table is expressed as a parametrized unit test. **Pass.** |
| V. Separate Mechanism from Domain Knowledge | Classification keys only on `pydantic-ai`'s provider-neutral exceptions and stdlib types. No provider SDK type or dataset fact enters the core (research.md §3). The redaction patterns are generic credential shapes. **Pass.** |
| VI. Deterministic Over Model Judgment | Classification, redaction, truncation, wait computation and summaries are all pure deterministic code. **Pass.** |
| VII. Code Quality / Simplicity | Only `max_attempts` is configurable (FR-020). Wait parameters are recorded but not exposed. No new Protocol (one classifier, one retry loop). No new dependency. The ~15-line loop is preferred over tenacity. **Pass.** |
| VIII. Security & Data Stewardship | Redaction is designed up front: exact removal of the configured key, then generic patterns, applied before truncation and before any log or persist (research.md §5). `TargetConfiguration` still carries no credential. **Pass.** |
| IX. CI Gate | Existing pytest + pyright CI covers the new modules and tests. **Pass.** |
| X. Usage as Research Data | `AgentRunLogEntry.failure` records every failed attempt, including chat sessions, one line per attempt (research.md §10). **Pass.** |
| Eng. 1 (thin wiring) | `failures.py` has no `pydantic_ai` import. `pydantic-ai`-aware rules are isolated in `transient.py`. `testset_runner` stays framework-free. **Pass.** |
| Eng. 2 (interface before 2nd impl) | No second implementation is anticipated, so no new Protocol. The existing `QuestionAnswerer` seam is reused as the retry boundary. **Pass.** |
| Eng. 3 (polymorphic dispatch) | N/A. The classification is a flat rule table over a type hierarchy, not format dispatch. |
| Eng. 4 (DI over globals) | `retry_policy` and `sleep` are injected parameters of `run_testset`. Secrets are passed explicitly to `describe_failure`. **Pass.** |
| Eng. 5 (validated boundary) | `FailureDetail` and `RetryPolicy` are pydantic models with field constraints. **Pass.** |
| Eng. 6 (testable without a model) | The retry loop is tested with fake answerers. The failure helpers are tested with plain exceptions. **Pass.** |
| Eng. 7 (typed centralized settings) | `RetryPolicy` is a typed, persisted object. The CLI flag / env fallback follows the existing `004` CLI convention. **Pass.** |
| Eng. 8 (versioned prompts) | Unaffected. |
| Eng. 9 (native instrumentation) | Logfire/OTel instrumentation is unchanged. The run-log/run-file records remain the structured research artifact, as in `003`/`004`. **Pass.** |
| Eng. 10 (static typing) | Full hints. pyright is in CI. **Pass.** |

**Post-design re-check (after Phase 1)**: still **Pass** on all rows. The design added no
Protocol, no dependency, and no configurable knob beyond FR-020. The only cross-package
coupling is `testset_runner` importing `FailureDetail` from `qa_agent.models`, the same
direction it already imports `RetrievalStep`.

## Project Structure

### Documentation (this feature)

```text
specs/006-agent-error-retry/
├── plan.md                         # This file
├── research.md                     # Phase 0
├── data-model.md                   # Phase 1
├── quickstart.md                   # Phase 1
├── contracts/
│   ├── failure-details.md          # qa_agent: FailureDetail production, redaction, classification
│   ├── running-with-retry.md       # run_testset retry loop + compare_runs additions
│   └── cli.md                      # --max-attempts, new report lines
├── checklists/requirements.md      # from /speckit-specify
└── tasks.md                        # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
src/
├── qa_agent/
│   ├── models.py            # + FailureDetail; QuestionAnsweringResult.failure; AgentRunLogEntry.failure
│   ├── failures.py          # NEW — root_cause, redact, truncate, describe_failure (no pydantic_ai import)
│   ├── transient.py         # NEW — TransientVerdict, classify(exc) over pydantic_ai.exceptions + stdlib
│   ├── capabilities.py      # both failure paths build a FailureDetail; _finalize logs/returns it
│   └── answerer.py          # passes api_key as a secret (via settings) — no behavior change otherwise
│
└── testset_runner/
    ├── models.py            # + RetryPolicy; QuestionResult.attempts/failed_attempts/failure;
    │                        #   RunSummary.errored_by_failure_type/retried_questions/errored_after_retries;
    │                        #   TestRun.retry_policy; RunComparison.retry_policy_a/b
    ├── runner.py            # retry loop, wait(k), summary extensions; retry_policy + sleep params
    ├── comparator.py        # populates retry_policy_a/b
    └── cli.py               # --max-attempts / QA_AGENT_MAX_ATTEMPTS; new report + compare lines

tests/
├── contract/
│   ├── qa_agent/test_failure_details.py         # NEW
│   └── testset_runner/
│       ├── test_retry.py                        # NEW
│       └── test_run_testset.py                  # + summary per-type/retry counts
├── unit/
│   ├── qa_agent/test_failures.py                # NEW
│   ├── qa_agent/test_transient.py               # NEW
│   └── testset_runner/{test_store,test_comparator,test_cli}.py   # + legacy-run, policy, flag cases
└── fixtures/testset_runner/pre-006-run.json     # NEW — pre-feature run file shape
```

**Structure Decision**: The same single-project layout as `001`–`005`. The feature is two new
`qa_agent` modules plus additive edits to existing modules. `web_ui`, `data_access` and
`dataset_selector` are untouched. `web_ui` benefits only through the run log.

## Complexity Tracking

No violations. Table intentionally left empty.
