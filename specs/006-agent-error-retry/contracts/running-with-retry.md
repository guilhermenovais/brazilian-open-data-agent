# Contract: Running a Testset with Bounded Retry

This extends `specs/004-testset-runner/contracts/running.md`. Everything in that contract still
holds unless this document replaces it.

```python
def run_testset(
    testset_path: str | Path,
    target: TargetConfiguration,
    *,
    answerer: QuestionAnswerer,
    matcher: MatchStrategy = NumericMatchStrategy(),
    store: RunStore,
    retry_policy: RetryPolicy = RetryPolicy(),        # NEW
    sleep: Callable[[float], None] = time.sleep,      # NEW, test seam (research.md §7)
) -> TestRun: ...
```

## Per-question loop (replaces "exactly one `answer()` call per question")

For each `Question`, in testset order:

1. Call `answerer.answer(question.question)`. Each call is fresh and gets nothing from earlier
   attempts (FR-015).
2. If the call did **not** error, grade the result and stop.
3. If it errored, append `result.failure` (if present) to `failed_attempts`. Stop when any of
   these holds:
   - `failure is None` or `failure.transient is False`: a non-transient failure, so no retry
     (FR-011, FR-013).
   - `attempts == retry_policy.max_attempts`: the attempts are used up (FR-012, FR-017).
4. Otherwise call `sleep(wait(k))` (data-model.md `RetryPolicy`), then go back to step 1.

The recorded `QuestionResult` uses the **last** attempt's answer, outcome, dataset key and steps.
It also records `attempts`, `failed_attempts`, and `failure` (the final failure, only when
errored). See data-model.md.

## Isolation guarantee (restated)

Nothing from one attempt is passed as input to another attempt or another question. The only
thing carried between attempts of the same question is bookkeeping (`attempts`,
`failed_attempts`), and it is never passed to the answerer.

## Persisted run

`TestRun.retry_policy` is set to the `retry_policy` argument (FR-022). `RunSummary` gains the
fields listed in data-model.md (FR-007, FR-019).

## Raises

The same as before: only `TestsetLoadError`, before any question is asked. A `KeyboardInterrupt`
during `sleep` propagates out, and `store.save` is never reached, so no partial run is persisted
(spec edge case).

## `compare_runs` (extends `specs/004-testset-runner/contracts/comparing.md`)

The signature is unchanged. `RunComparison` gains `retry_policy_a` / `retry_policy_b`, and each is
`None` for pre-feature runs (FR-023, FR-024). Transitions still depend only on `match_status`.

## Behavioral requirements (traceability)

| Scenario / Requirement | Behavior |
|------------------------|----------|
| US2 AS1 | Transient failure, then success: graded on attempt 2, `attempts=2`, `failed_attempts` has 1 entry, `failure=None`. |
| US2 AS2 | Transient failure on every attempt: `attempts == max_attempts`, `match_status="errored"`, `failed_attempts` has `max_attempts` entries, `failure == failed_attempts[-1]`. |
| US2 AS3 / SC-003 | Non-transient failure: `attempts=1`, and `sleep` is never called. |
| US2 AS4 / FR-016 | `steps` equals the successful attempt's `steps`. |
| US2 AS5 / FR-019 | `summary.retried_questions` and `summary.errored_after_retries`. |
| US3 AS1–2 / FR-020 | `answer()` is called at most `max_attempts` times per question. With `max_attempts=1` there is never a retry. |
| US3 AS3 / FR-022 | `run.retry_policy == retry_policy`, and it is persisted. |
| US3 AS4 / FR-023 | `RunComparison.retry_policy_a/b`. |
| FR-014 | Calls to `sleep` equal the `wait(k)` sequence. A provider `retry_after_seconds` raises the wait up to `max_wait_seconds` and never beyond. |
| SC-002 | Every question fails once transiently and then succeeds: zero errored, every `attempts == 2`. |
| FR-024 / SC-006 | A pre-feature run file loads, and `compare_runs` works against a new run. |
