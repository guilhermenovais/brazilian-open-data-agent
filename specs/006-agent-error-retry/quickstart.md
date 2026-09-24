# Quickstart: Validating Agent Error Details and Bounded Retry

This guide checks that the feature works end to end. For behavior details, see
[contracts/](./contracts/) and [data-model.md](./data-model.md).

## Prerequisites

```bash
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
```

## Track 1: Automated (CI gate, no model or network)

```bash
.venv/bin/pytest                      # full suite, includes the new tests below
.venv/bin/pyright                     # type-check src/
```

| Scenario | Test location | Proves |
|----------|---------------|--------|
| 1. Errored question carries type and message | `tests/contract/qa_agent/test_failure_details.py` | US1 AS1, AS2, AS5; FR-001–004, FR-008, FR-009 |
| 2. Credential echoed by provider is redacted | same file | US1 AS4; FR-005; SC-004 |
| 3. Long / empty / wrapped messages | `tests/unit/qa_agent/test_failures.py` | FR-004, FR-006, edge cases |
| 4. Transient/non-transient classification table | `tests/unit/qa_agent/test_transient.py` | FR-010, FR-011 |
| 5. Transient then success is graded, attempts=2 | `tests/contract/testset_runner/test_retry.py` | US2 AS1, AS4; SC-002 |
| 6. Retries exhausted, then errored with all failures | same file | US2 AS2; FR-017, FR-018 |
| 7. Non-transient is not retried | same file | US2 AS3; SC-003 |
| 8. Wait sequence and Retry-After cap | same file (fake `sleep`) | FR-014 |
| 9. `max_attempts=1` disables retry; policy persisted | same file | US3 AS1–3; FR-020–022 |
| 10. Summary: per-type counts, retried, exhausted | `tests/contract/testset_runner/test_run_testset.py` | US1 AS3; US2 AS5; FR-007, FR-019 |
| 11. Pre-feature run loads and compares | `tests/unit/testset_runner/test_store.py`, `test_comparator.py` (fixture `tests/fixtures/testset_runner/pre-006-run.json`) | FR-023, FR-024; SC-006 |
| 12. `--max-attempts` / env fallback / rejects 0 | `tests/unit/testset_runner/test_cli.py` | FR-020, FR-021 |

**Expected result**: the whole suite passes. The existing `004`/`005` tests pass without
changes, except `test_cli.py`'s fake `run_testset` signature, which gains `retry_policy`.

## Track 2: Manual, against real failure conditions

### A. Unreachable target (US1 Independent Test, SC-005)

```bash
.venv/bin/python -m testset_runner.cli run \
  --testset data/testsets/orcamentos-aeb-csv-10.json \
  --model some-model --base-url http://127.0.0.1:9/v1 --api-key sk-test-DO-NOT-LEAK-1234567890
```

Expected:
- The run completes, and the `target unreachable` WARNING is followed by
  `Most common failure: ConnectError (10 questions)`.
- `Errored after exhausting retries: 10`. Each question shows `attempts: 3` in the saved JSON.
- `grep -r "DO-NOT-LEAK" data/testset_runs/ data/logs/` finds nothing (SC-004).
- `data/logs/qa_agent_runs.jsonl` has 30 new lines (10 questions × 3 attempts), each with a
  `failure`.

### B. Non-transient failure fails fast (US2 AS3)

Rerun A against a real endpoint with an invalid API key or an unknown model name. Expected:
`AuthenticationError` or `NotFoundError` counts in the summary, `attempts: 1` for every
question, and no waits between questions.

### C. Retries disabled and the policy compared (US3 Independent Test)

```bash
.venv/bin/python -m testset_runner.cli run --testset data/testsets/orcamentos-aeb-csv-10.json \
  --model some-model --base-url http://127.0.0.1:9/v1 --max-attempts 1
.venv/bin/python -m testset_runner.cli compare data/testset_runs/<run-A>.json data/testset_runs/<run-C>.json
```

Expected: run C shows `attempts: 1` everywhere. The comparison prints each run's retry policy
(`max_attempts=3` vs `max_attempts=1`).

### D. Pre-feature run compatibility (SC-006)

Compare any run file saved before this feature against a new run. Expected: no error, and the
old side prints `retry policy: not recorded`.

## Note on attempt counts

One *attempt* is one full, fresh answer to the question. Inside an attempt, the OpenAI SDK may
retry an individual HTTP request up to 2 more times on its own (research.md §2). So in scenario
A, the wall-clock time per question is longer than the question-level waits alone.

## Validation notes (2026-09-24)

Track 2 scenarios A, C and D were run against `http://127.0.0.1:9/v1` and behaved as
expected, with these observations:

- **A**: the recorded message for `ConnectError` was `"All connection attempts failed"`,
  not `"[Errno 111] Connection refused"`. That is the `httpx` wording for this failure; the
  type and transient verdict are as expected. The 10-question run took about 1 min 43 s,
  mostly the SDK's own request-level retries inside each attempt (see the note above). No
  `DO-NOT-LEAK` in the run file or in `data/logs/qa_agent_runs.jsonl`, which gained 30
  `ConnectError` lines.
- **C**: with `--max-attempts 1`, `Errored after exhausting retries` is `10`, not `0`. This
  matches the data-model definition (final failure transient and `attempts == max_attempts`):
  a single allowed attempt counts as exhausted.
- **D**: the pre-feature run `data/testset_runs/20260921T103437122660Z.json` compared against
  a new run of the same testset without error, printing `retry policy: not recorded` for it.
- **B** (real endpoint with a bad key) was not run: it needs live provider credentials. Its
  behavior is covered by the 401/404 cases in `tests/contract/qa_agent/test_failure_details.py`
  and the non-transient case in `tests/contract/testset_runner/test_retry.py`.
