# Data Model: Agent Error Details and Bounded Retry

**Feature**: `006-agent-error-retry` | **Date**: 2026-09-24

All changes are **additive**. Every new field on a persisted model is optional, so run files
and log lines written before this feature still validate (FR-024, research.md §9).

---

## New: `FailureDetail` (`qa_agent/models.py`)

Describes one failure. It crosses the `qa_agent` → `testset_runner` boundary and is persisted
in run files and the run log.

| Field | Type | Rules |
|-------|------|-------|
| `type` | `str` | Class name of the **root** exception in the cause chain (research.md §4). For dataset-selection failures, the selector exception's class name (e.g. `NoBriefingsAvailableError`). Non-empty. |
| `message` | `str` | `str(root_exception)`. Credentials are removed first (FR-005, research.md §5), then the text is capped at 2,000 characters with a `… [truncated N characters]` marker (FR-006). May be `""`, and is never replaced with a placeholder. |
| `transient` | `bool` | `True` only if a transient rule matches some link of the chain (research.md §3). Always `False` for dataset-selection failures and for anything unrecognized (FR-011). |
| `retry_after_seconds` | `float \| None` | Provider-suggested wait (`ModelHTTPError.retry_after`) when present, otherwise `None`. Stored exactly as the provider gave it. The cap is applied only when waiting. |

Constructed only by `qa_agent.failures.describe_failure(...)` and by the dataset-selection
branch of `answer_question`. No other code builds one from a raw exception.

---

## New: `RetryPolicy` (`testset_runner/models.py`)

The retry rules for one run. Persisted on `TestRun` (FR-022).

| Field | Type | Default | Rules |
|-------|------|---------|-------|
| `max_attempts` | `int` | `3` | `ge=1`. The total attempts per question, including the first. `1` disables retries (FR-020, FR-021). |
| `initial_wait_seconds` | `float` | `2.0` | `ge=0`. The wait before the first retry. |
| `backoff_multiplier` | `float` | `2.0` | `ge=1`. The wait grows by this factor for each further retry. |
| `max_wait_seconds` | `float` | `60.0` | `ge=0`. The upper bound on any single wait, including one set by the provider. |

Derived behavior (a pure function in `runner.py`, research.md §7):
`wait(k) = min(max(initial × multiplier^(k-1), retry_after or 0), max_wait)` for retry `k ≥ 1`.

Note: an "attempt" is one `QuestionAnswerer.answer()` call. The provider SDK may retry
individual HTTP requests inside one attempt (research.md §2).

---

## Extended: `QuestionAnsweringResult` (`qa_agent/models.py`)

| Field | Change |
|-------|--------|
| `failure: FailureDetail \| None = None` | **New.** Set whenever `errored=True` by the production path (`answer_question`). `None` when the question was answered normally (FR-002). |
| `answer`, `dataset_key`, `outcome`, `steps`, `errored` | Unchanged. `answer` keeps the same fixed Portuguese text on failure (FR-009). |

Invariant (production path): `errored ⇔ failure is not None`. This is **not** enforced by a
validator, so existing third-party or test `QuestionAnswerer` fakes that return
`errored=True` without a `failure` stay valid. The runner treats such a result as a
non-transient failure with no details.

---

## Extended: `AgentRunLogEntry` (`qa_agent/models.py`)

| Field | Change |
|-------|--------|
| `failure: FailureDetail \| None = None` | **New.** Same value as the returned result's `failure` (FR-008). One log entry per attempt (research.md §10). |

---

## Extended: `QuestionResult` (`testset_runner/models.py`)

| Field | Type | Rules |
|-------|------|-------|
| `attempts` | `int \| None = None` | **New.** Number of `answer()` calls made for this question, `1 ≤ attempts ≤ retry_policy.max_attempts`. `None` means not recorded (pre-feature run). |
| `failed_attempts` | `list[FailureDetail] = []` | **New.** The `FailureDetail` of every failed attempt in order, including failures that came before a successful attempt (FR-018). Length is `attempts - 1` when the question succeeded, and `attempts` when it ended errored. |
| `failure` | `FailureDetail \| None = None` | **New.** The final failure when `match_status == "errored"` (FR-017), equal to `failed_attempts[-1]`. `None` for every non-errored question (FR-002). |
| `actual_answer`, `agent_outcome`, `dataset_key`, `steps`, `match_status` | Unchanged in meaning. They always come from the **last** attempt, which is the successful one when any succeeded (FR-016). |

---

## Extended: `RunSummary` (`testset_runner/models.py`)

Still derived only from `results`. These fields apply both at run level and inside each
`by_category` entry.

| Field | Type | Definition |
|-------|------|------------|
| `errored_by_failure_type` | `dict[str, int] \| None = None` | **New.** For errored questions, a count per `failure.type`. Errored results with no recorded failure are counted under `"unknown"` (FR-007). |
| `retried_questions` | `int \| None = None` | **New.** Count of results with `attempts > 1` (FR-019). |
| `errored_after_retries` | `int \| None = None` | **New.** Count of errored results whose final failure was transient and whose `attempts == max_attempts`, meaning the attempts ran out (FR-019). |
| existing fields | unchanged | `target_unreachable` logic is unchanged. When it is `True`, the CLI now also prints the top failure type(s) (spec edge case). |

---

## Extended: `TestRun` (`testset_runner/models.py`)

| Field | Change |
|-------|--------|
| `retry_policy: RetryPolicy \| None = None` | **New.** The policy used. Always set by the new `run_testset`. `None` means a pre-feature run (FR-022, FR-024). |

`TargetConfiguration` is **unchanged**. It stays "the model/URL targeted". The retry policy is
a run condition, not a target property.

---

## Extended: `RunComparison` (`testset_runner/models.py`)

| Field | Change |
|-------|--------|
| `retry_policy_a: RetryPolicy \| None = None` | **New.** Run A's policy, or `None` if not recorded (FR-023). |
| `retry_policy_b: RetryPolicy \| None = None` | **New.** Run B's policy. |

A difference in policy **never** changes transitions or blocks a comparison. It is information
only (spec Assumptions). Only `content_hash` mismatch raises `IncompatibleRunsError`, as before.

---

## State: one question's attempts (runner loop)

```text
attempt 1 ──answer()──► success ─────────────────────────────► graded (attempts=k)
   ▲                  └► failure ─┬─ non-transient ──────────► errored (attempts=k)
   │                              ├─ transient, k == max ────► errored (attempts=k, exhausted)
   └── sleep(wait(k)) ◄───────────┴─ transient, k < max
```

Each arrow back to `answer()` is a brand-new call: nothing from the failed attempt is passed
back in (FR-015).
