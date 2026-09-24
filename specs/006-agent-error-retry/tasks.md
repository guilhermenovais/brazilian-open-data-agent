---

description: "Task list for 006-agent-error-retry"
---

# Tasks: Agent Error Details and Bounded Retry

**Input**: Design documents from `/specs/006-agent-error-retry/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (failure-details.md, running-with-retry.md, cli.md), quickstart.md

**Tests**: Included. Constitution IV and plan.md ask for them, and quickstart.md maps each scenario to a test file. Within each story, write the tests first and confirm they fail before implementing.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Single project: `src/qa_agent/`, `src/testset_runner/`, `tests/{contract,unit,fixtures}/<package>/` at the repository root.

Standing constraints for every task (from plan.md):
- `src/testset_runner/` MUST NOT import `pydantic_ai`.
- `src/qa_agent/failures.py` MUST NOT import `pydantic_ai`. Only `src/qa_agent/transient.py` may.
- Every new field on a persisted model MUST be optional with a default, so pre-feature run files and log lines still validate (FR-024).
- The user-facing `answer` texts (`_NO_DATASET_ANSWER`, `_PROCESSING_FAILED_ANSWER` in `src/qa_agent/capabilities.py`) MUST NOT change (FR-009).
- No new dependency. Do not use `tenacity` (research.md §1).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm a green baseline and capture the pre-feature run file shape before any model changes.

- [X] T001 Run `.venv/bin/pytest` and `.venv/bin/pyright` from the repo root and confirm both pass on the current `main`, so later failures can be attributed to this feature
- [X] T002 [P] Create the pre-feature run fixture `tests/fixtures/testset_runner/pre-006-run.json`. It is a `TestRun` JSON matching the **current** `src/testset_runner/models.py` exactly (no `retry_policy`, no `attempts`/`failed_attempts`/`failure` on results, no `errored_by_failure_type`/`retried_questions`/`errored_after_retries` in the summary or `by_category` entries). Use the same `testset` as `tests/fixtures/testset_runner/mini-testset.json` (same `content_hash`) so it can be compared against a new run of that testset. Include at least one `errored` result and one `matched` result. Produce it with the current code (e.g. `TestRun(...).model_dump_json(indent=2)` in a scratch script) rather than by hand, so it is a faithful pre-feature shape

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared `FailureDetail` model that crosses the `qa_agent` → `testset_runner` boundary. Every story depends on it.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Add `class FailureDetail(BaseModel)` to `src/qa_agent/models.py`, with a docstring saying it describes one failure, is built only by `qa_agent.failures.describe_failure` / the dataset-selection branch of `answer_question`, and is persisted in run files and the run log. Fields (data-model.md):
  - `type: str = Field(min_length=1)`: "Class name of the **root** exception in the cause chain"
  - `message: str`: credential-free and length-capped. "May be `""`, and is never replaced with a placeholder."
  - `transient: bool`: "`True` only if a transient rule matches some link of the chain". "Always `False` for dataset-selection failures and for anything unrecognized"
  - `retry_after_seconds: float | None = None`: "Stored exactly as the provider gave it. The cap is applied only when waiting."
- [X] T004 In `src/qa_agent/models.py`, add `failure: FailureDetail | None = None` to `QuestionAnsweringResult` and to `AgentRunLogEntry`. Do **not** add a validator enforcing `errored ⇔ failure is not None` (data-model.md: existing fakes returning `errored=True` without `failure` must stay valid). Run `.venv/bin/pytest tests/unit/qa_agent/test_run_log.py` to confirm old log entries still validate

**Checkpoint**: `FailureDetail` exists and all existing tests still pass.

---

## Phase 3: User Story 1 - See why a question errored (Priority: P1) 🎯 MVP

**Goal**: Every errored question (dataset selection or agent run) carries the root-cause failure type and a redacted, length-capped message. The failure is persisted in the run file and the run log, and the run summary counts errored questions per failure type.

**Independent Test**: Run a testset with a fake answerer (or against `--base-url http://127.0.0.1:9/v1`) where every question fails. The saved run shows `failure.type`/`failure.message` on every errored question and none on answered ones. `summary.errored_by_failure_type` counts them, the CLI prints `Errored by failure type:` and `Most common failure: ...`, and the configured API key appears nowhere in `data/testset_runs/` or `data/logs/`.

### Tests for User Story 1 ⚠️

> Write these first and confirm they FAIL before implementing.

- [X] T005 [P] [US1] Create `tests/unit/qa_agent/test_failures.py` covering `qa_agent.failures` (functions do not exist yet). Name tests after the behavior they state:
  - `root_cause`: follows `__cause__`. Falls back to `__context__`. Ignores `__context__` when `__suppress_context__` is `True`. Stops on a cycle (build two exceptions whose `__cause__` point at each other). Returns the exception itself when there is no chain
  - `redact`: replaces an exact configured secret (e.g. `"sk-test-DO-NOT-LEAK-1234567890"` and a non-`sk-` secret like `"plainsecretvalue"`) with `[REDACTED]`. Ignores `None` and `""` secrets. Pattern pass redacts `Bearer abc.def-123`, an `sk-` key with ≥ 16 chars after the prefix, and `api_key=...`, `api-key: ...`, `apikey=...`, `token=...`, `authorization: ...`, `key=...`. Leaves ordinary text such as `"Connection refused"` unchanged
  - `truncate`: a message of exactly `MAX_MESSAGE_CHARS` (2000) is unchanged. A 2500-char message becomes its first 2000 chars + `"… [truncated 500 characters]"`. `""` stays `""`
  - `describe_failure`: `type`/`message` come from the root (e.g. `RuntimeError("outer")` raised from `TimeoutError("read timed out")` → `type == "TimeoutError"`, `message == "read timed out"`). A secret split across the 2000-char boundary is still fully redacted (redact runs before truncate). `transient` and `retry_after_seconds` come from the injected `classify` callable, which receives the **original** (outer) exception, not the root. An empty-message exception yields `message == ""`
- [X] T006 [P] [US1] Create `tests/contract/qa_agent/test_failure_details.py`. Follow the `FunctionModel`/`_answer_with_selection(model_override=...)` pattern already used in `tests/contract/qa_agent/test_failure_translation.py`, and use an in-memory recording `RunLogger`. Cases (US1 AS1, AS2, AS4, AS5; FR-001–FR-005, FR-008, FR-009):
  - the model raises `ModelHTTPError(status_code=401, model_name=..., body=...)` raised from a `RuntimeError("bad key")` → `errored`, `failure.type == "RuntimeError"`, `failure.message == "bad key"`, and the answer text equals the pre-feature `_PROCESSING_FAILED_ANSWER`
  - the model raises `ValueError("boom")` → `failure.type == "ValueError"`, `failure.message == "boom"`
  - the model raises an exception whose message echoes `settings.api_key` (`AgentSettings(model_name="test", api_key="sk-test-DO-NOT-LEAK-1234567890")`) → `"DO-NOT-LEAK"` is absent from both the returned `failure.message` and the logged `AgentRunLogEntry.failure.message`
  - dataset selection raises `NoBriefingsAvailableError` (use `answer_question` with a selector fake that raises) → `failure.type == "NoBriefingsAvailableError"`, `failure.transient is False`, and the answer text equals `_NO_DATASET_ANSWER`
  - normal completion → `failure is None` on both the result and the log entry
  - every case: exactly one `AgentRunLogEntry` is logged, and its `failure` equals the result's `failure`
- [X] T007 [P] [US1] Extend `tests/contract/testset_runner/test_run_testset.py` with a fake answerer that returns scripted `QuestionAnsweringResult`s: errored ones with `FailureDetail(type="ConnectError", message="[Errno 111] Connection refused", transient=False)` and `FailureDetail(type="AuthenticationError", ...)`, plus answered ones. Assert (US1 AS1–AS3; FR-002, FR-007):
  - each errored `QuestionResult.failure` equals the answerer's `failure`
  - every non-errored result has `failure is None`
  - `summary.errored_by_failure_type == {"ConnectError": n1, "AuthenticationError": n2}`, including inside the matching `summary.by_category[...]` entries
  - an errored result with `failure=None` (legacy fake) is counted under `"unknown"`
  - `summary.errored_by_failure_type == {}` when nothing errored
- [X] T008 [P] [US1] Extend `tests/unit/testset_runner/test_store.py`: `JsonFileRunStore` loads `tests/fixtures/testset_runner/pre-006-run.json` without error, every result has `failure is None`, and `summary.errored_by_failure_type is None` (FR-024, SC-006)
- [X] T009 [P] [US1] Extend `tests/unit/testset_runner/test_cli.py` (`run` subcommand, using the existing fake `run_testset` pattern) so the fake returns a `TestRun` with errored results. Assert that stdout contains `Errored by failure type:` followed by indented `  <type>: <count>` lines sorted by count descending. When `target_unreachable` is `True`, the WARNING line is followed by `Most common failure: <type> (<count> questions)`. When nothing errored, the `Errored by failure type:` block is absent (contracts/cli.md)

### Implementation for User Story 1

- [X] T010 [US1] Create `src/qa_agent/failures.py` (no `pydantic_ai` import). Give it a module docstring summarizing research.md §4–§6: root-cause choice, redact→truncate order, and why the class name is used rather than the qualname. Implement:
  - `MAX_MESSAGE_CHARS = 2000`
  - `class TransientVerdict(NamedTuple): transient: bool; retry_after_seconds: float | None`, defined here so `failures.py` stays framework-free; `transient.py` re-exports it
  - `root_cause(exc: BaseException) -> BaseException`: follow `__cause__`, else `__context__` unless `__suppress_context__`, stop at end or on a cycle (track `id()`s)
  - `redact(message: str, secrets: Iterable[str | None]) -> str`: exact pass first (every non-empty secret → `[REDACTED]`), then compiled generic patterns (research.md §5)
  - `truncate(message: str, limit: int = MAX_MESSAGE_CHARS) -> str`: appends `f"… [truncated {n} characters]"`
  - `describe_failure(exc, *, secrets, classify: Callable[[BaseException], TransientVerdict]) -> FailureDetail`: root → `type(root).__name__`, `truncate(redact(str(root), secrets))`, and `classify(exc)` for `transient`/`retry_after_seconds`
  - `never_transient(exc: BaseException) -> TransientVerdict`: returns `TransientVerdict(False, None)`. Used for dataset-selection failures and, until US2, the agent path

  Make T005 pass.
- [X] T011 [US1] Update `src/qa_agent/capabilities.py`:
  - capture the exception in both `except` branches (`except (...) as exc:` / `except Exception as exc:`)
  - build `failure = describe_failure(exc, secrets=[settings.api_key], classify=never_transient)` in each (dataset-selection branch: FR-003/FR-010, always `never_transient`)
  - add a `failure: FailureDetail | None = None` parameter to `_finalize`, which passes it to both `AgentRunLogEntry(failure=...)` and `QuestionAnsweringResult(failure=...)`
  - update the module docstring to say failures are now described (type/message/transient) rather than discarded
  - keep the answer texts unchanged (FR-009)

  `src/qa_agent/answerer.py` needs no change, since `settings.api_key` already reaches `answer_question`. Make T006 pass (transient assertions are added in US2).
- [X] T012 [US1] In `src/testset_runner/models.py`, add `failure: FailureDetail | None = None` to `QuestionResult` (import `FailureDetail` from `qa_agent.models`, alongside the existing `RetrievalStep` import), and `errored_by_failure_type: dict[str, int] | None = None` to `RunSummary`, documented as "For errored questions, a count per `failure.type`. Errored results with no recorded failure are counted under `"unknown"`" and `None` meaning not recorded
- [X] T013 [US1] Update `src/testset_runner/runner.py`: set `failure=answer_result.failure if answer_result.errored else None` on each `QuestionResult`, and in `_tally` compute `errored_by_failure_type` over results with `match_status == "errored"` (key `r.failure.type if r.failure else "unknown"`). Always set it, including `{}`, for both the run level and each `by_category` entry. Make T007 and T008 pass
- [X] T014 [US1] Update `_run` in `src/testset_runner/cli.py` per contracts/cli.md:
  - after the existing summary lines, print `Errored by failure type:` and `  <type>: <count>` lines (count descending, then type name) only when at least one question errored
  - directly after the existing `target unreachable` WARNING, print `Most common failure: <type> (<count> questions)` for the top type(s)
  - never print a credential

  Make T009 pass.

**Checkpoint**: US1 is fully functional. Errored questions show why they failed in the run file, run log, and CLI output. No retries yet (every question is attempted once).

---

## Phase 4: User Story 2 - Transient failures don't count against the agent (Priority: P2)

**Goal**: Classify failures as transient/non-transient, and retry a question from scratch on transient failures with increasing, `Retry-After`-aware, capped waits, up to the default 3 attempts. Record every attempt's failure, and summarize retried and exhausted questions.

**Independent Test**: With a scripted fake answerer and a recording fake `sleep`, a question that fails transiently once and then succeeds is graded normally with `attempts=2` and one entry in `failed_attempts`. A question that fails transiently every time stops at 3 attempts, errored. A non-transient failure is attempted exactly once, with no `sleep`.

### Tests for User Story 2 ⚠️

> Write these first and confirm they FAIL before implementing.

- [X] T015 [P] [US2] Create `tests/unit/qa_agent/test_transient.py`, a parametrized classification table for `qa_agent.transient.classify` (research.md §3, FR-010/FR-011) using real `pydantic_ai.exceptions` instances:
  - transient: `ModelHTTPError` with `status_code` 408, 425, 429, 500, 502, 503, 504 and 529; plain `ModelAPIError`; `TimeoutError`; `ConnectionError`; `ConnectionRefusedError`; `UnexpectedModelBehavior` raised **from** a `TimeoutError` (chain rule)
  - non-transient: `ModelHTTPError` 400, 401, 403, 404, 409, 422 and 501; `UnexpectedModelBehavior("...")` alone; `UsageLimitExceeded`; `ValueError`; `RuntimeError`
  - `retry_after_seconds`: a 429 `ModelHTTPError` carrying a `retry_after` value returns it unchanged, and one without returns `None`. When the chain has several `ModelHTTPError`s, the first one that carries a `retry_after` wins

  Check how `ModelHTTPError` exposes `retry_after` in the installed `pydantic-ai` 2.45.0 (`.venv/lib/python3.12/site-packages/pydantic_ai/exceptions.py`) and construct it accordingly.
- [X] T016 [P] [US2] Extend `tests/contract/qa_agent/test_failure_details.py` with transient assertions via `FunctionModel`:
  - 429 with a retry-after → `transient is True`, `retry_after_seconds` set
  - 503 → `transient is True`
  - 401 and 404 → `transient is False`
  - plain `ModelAPIError` → `True`
  - `TimeoutError` wrapped in a `RuntimeError` → `True`, with `type == "TimeoutError"`
  - `ValueError` → `False`
  - the dataset-selection failure stays `False`
- [X] T017 [P] [US2] Create `tests/contract/testset_runner/test_retry.py`. Use a scripted fake answerer (`dict[question_text, list[QuestionAnsweringResult]]`, popping one per call and recording call counts), a recording fake `sleep` (appends each wait to a list), the existing in-memory/tmp `RunStore` pattern from `test_run_testset.py`, and `tests/fixtures/testset_runner/mini-testset.json`. Cases (from the contracts/running-with-retry.md traceability table):
  - **US2 AS1 / AS4 / FR-016**: transient failure, then success → graded on attempt 2's answer, `attempts == 2`, `len(failed_attempts) == 1`, `failure is None`, and `steps` equals the second result's `steps`
  - **US2 AS2 / FR-017 / FR-018**: transient on every attempt → `attempts == 3`, `match_status == "errored"`, `len(failed_attempts) == 3`, `failure == failed_attempts[-1]`, and the next question is still answered
  - **US2 AS3 / SC-003**: non-transient failure → `attempts == 1`, answerer called once, and `sleep` never called
  - errored result with `failure=None` (legacy fake) → treated as non-transient, `attempts == 1`, `failed_attempts == []`
  - **SC-002**: every question fails transiently once and then succeeds → `summary.by_status` has no `errored`, and every `attempts == 2`
  - **FR-014 wait sequence**: default policy, all transient → `sleep` calls `== [2.0, 4.0]`. With `RetryPolicy(max_attempts=5)` → `[2.0, 4.0, 8.0, 16.0]`
  - **FR-014 Retry-After**: `retry_after_seconds=30` on the first failure → first wait `30.0`. `retry_after_seconds=1` → first wait stays `2.0` (a suggestion never shortens the backoff). `retry_after_seconds=500` → wait capped at `60.0`
  - **US2 AS5 / FR-019**: a mix of results → `summary.retried_questions` counts `attempts > 1`, and `summary.errored_after_retries` counts errored results whose final failure is transient and whose `attempts == max_attempts`. Check that a non-transient errored question is **not** counted
  - a `KeyboardInterrupt` raised by the fake `sleep` propagates out of `run_testset`, and `store.save` is never called
- [X] T018 [P] [US2] Add a pure-function unit test for the wait computation in `tests/contract/testset_runner/test_retry.py` (or alongside it): `_wait(policy, k, retry_after)` equals `min(max(initial × multiplier^(k-1), retry_after or 0), max_wait)` for k = 1..4, with and without `retry_after`, and with `initial_wait_seconds=0`
- [X] T019 [P] [US2] Extend `tests/unit/testset_runner/test_cli.py` (`run`): when the fake `run_testset` returns a run whose summary has `retried_questions=4` and `errored_after_retries=1`, stdout contains `Questions retried: 4` and `Errored after exhausting retries: 1`, and prints `not recorded` for either one when it is `None` (contracts/cli.md)

### Implementation for User Story 2

- [X] T020 [US2] Create `src/qa_agent/transient.py`, the only module in this feature that imports `pydantic_ai`. Give it a module docstring that restates the research.md §3 rule table and the "any link in the chain" and "unknown → non-transient" decisions. Implement:
  - re-export `TransientVerdict` from `qa_agent.failures`
  - `classify(exc: BaseException) -> TransientVerdict`: walk the chain with the same link rule as `root_cause` (expose a shared `iter_chain(exc)` generator in `failures.py` and use it in both). Transient if any link is `ModelHTTPError` with `status_code in {408, 425, 429}` or `500 <= status_code <= 599 and status_code != 501`; or a `ModelAPIError` that is not a `ModelHTTPError`; or an instance of `TimeoutError` / `ConnectionError`
  - `retry_after_seconds` comes from the first `ModelHTTPError` in the chain with a non-`None` retry-after, as a `float`

  Make T015 pass.
- [X] T021 [US2] In `src/qa_agent/capabilities.py`, switch the agent-run `except Exception as exc:` branch to `classify=transient.classify`. The dataset-selection branch keeps `never_transient` (FR-010). Make T016 pass
- [X] T022 [US2] In `src/testset_runner/models.py`, add `class RetryPolicy(BaseModel)`:
  - `max_attempts: int = Field(default=3, ge=1)`
  - `initial_wait_seconds: float = Field(default=2.0, ge=0)`
  - `backoff_multiplier: float = Field(default=2.0, ge=1)`
  - `max_wait_seconds: float = Field(default=60.0, ge=0)`

  Its docstring must state: "an attempt is one `QuestionAnswerer.answer()` call. The provider SDK (e.g. openai, `DEFAULT_MAX_RETRIES = 2`) may retry individual HTTP requests inside one attempt, so `attempts=1` does not mean exactly one HTTP request" (research.md §2, Constitution III). Also give the wait formula.
- [X] T023 [US2] In `src/testset_runner/models.py`, extend `QuestionResult` with:
  - `attempts: int | None = None`: "`1 ≤ attempts ≤ retry_policy.max_attempts`. `None` means not recorded (pre-feature run)"
  - `failed_attempts: list[FailureDetail] = []`: "Length is `attempts - 1` when the question succeeded, and `attempts` when it ended errored"

  Extend `RunSummary` with `retried_questions: int | None = None` and `errored_after_retries: int | None = None`.
- [X] T024 [US2] Implement the retry loop in `src/testset_runner/runner.py` per contracts/running-with-retry.md:
  - add keyword params `retry_policy: RetryPolicy = RetryPolicy()` and `sleep: Callable[[float], None] = time.sleep` to `run_testset`
  - add a pure `_wait(policy: RetryPolicy, k: int, retry_after: float | None) -> float`
  - per question, loop calling `answerer.answer(question.question)` fresh each time (FR-015). On error, append `result.failure` to `failed_attempts` if not `None`. Stop if `failure is None or not failure.transient` or `attempts == retry_policy.max_attempts`. Otherwise `sleep(_wait(retry_policy, attempts, failure.retry_after_seconds))` and retry
  - build `QuestionResult` from the **last** result, with `attempts`, `failed_attempts`, and `failure` (final failure only when errored)
  - pass `max_attempts` into `_summarize`/`_tally` to compute `retried_questions` and `errored_after_retries` at the run level and per category

  Make T017 and T018 pass, and re-run T007's tests.
- [X] T025 [US2] Update `_run` in `src/testset_runner/cli.py` to print `Questions retried: <n>` and `Errored after exhausting retries: <n>` after the existing summary lines (printing `not recorded` for `None`), before the `Errored by failure type:` block. Make T019 pass

**Checkpoint**: US1 and US2 both work. Transient failures are retried with the default policy (3 attempts), and non-transient failures fail fast.

---

## Phase 5: User Story 3 - Control and record the retry policy (Priority: P3)

**Goal**: A person can set `--max-attempts` (or `QA_AGENT_MAX_ATTEMPTS`) without editing code. The policy is persisted with the run, shown in the run output, and stated for both runs in a comparison. Pre-feature runs show `not recorded`.

**Independent Test**: Run the same testset with `--max-attempts 1` and with the default, and check that each saved run's `retry_policy` matches. Then `compare` the two runs and the pre-feature fixture against a new run, and confirm each side prints its `retry policy:` line or `not recorded`.

### Tests for User Story 3 ⚠️

> Write these first and confirm they FAIL before implementing.

- [X] T026 [P] [US3] Extend `tests/contract/testset_runner/test_retry.py`:
  - **US3 AS1**: `RetryPolicy(max_attempts=2)` with always-transient failures → the answerer is called at most 2 times per question
  - **US3 AS2**: `RetryPolicy(max_attempts=1)` with a transient failure → `attempts == 1`, and `sleep` is never called
  - **US3 AS3 / FR-022**: `run.retry_policy == retry_policy`, and the policy survives a `store.save` → `store.load` round trip
- [X] T027 [P] [US3] Extend `tests/unit/testset_runner/test_comparator.py`:
  - comparing two runs with different policies sets `retry_policy_a`/`retry_policy_b` accordingly, and leaves transitions unchanged (information only)
  - comparing `tests/fixtures/testset_runner/pre-006-run.json` against a new run of the same testset succeeds with `retry_policy_a is None` (FR-023, FR-024, SC-006)
- [X] T028 [P] [US3] Extend `tests/unit/testset_runner/test_cli.py`. First update the existing fake `run_testset` to accept `retry_policy` (quickstart.md notes this as the one expected existing-test change). Then:
  - `--max-attempts 5` → the fake receives `RetryPolicy(max_attempts=5)`
  - with no flag and `QA_AGENT_MAX_ATTEMPTS=2` in the env (use `monkeypatch.setenv`) → `max_attempts=2`
  - with neither → `max_attempts=3`
  - `--max-attempts 0`, `-1` and `abc` (and env `QA_AGENT_MAX_ATTEMPTS=0`) → stderr `Error: --max-attempts must be an integer >= 1.`, exit code `1`, and the fake is never called
  - `run` output contains `Retry policy: max_attempts=3, waits 2.0s x2.0 (cap 60.0s)`
  - `compare` output has `  retry policy: max_attempts=...` after each `Run A:`/`Run B:` line, and `  retry policy: not recorded` for a run with `retry_policy=None`

### Implementation for User Story 3

- [X] T029 [US3] In `src/testset_runner/models.py`, add `retry_policy: RetryPolicy | None = None` to `TestRun` (docstring: `None` means a pre-feature run), and `retry_policy_a: RetryPolicy | None = None` / `retry_policy_b: RetryPolicy | None = None` to `RunComparison`. Leave `TargetConfiguration` unchanged
- [X] T030 [US3] In `src/testset_runner/runner.py`, set `retry_policy=retry_policy` on the constructed `TestRun`. Make T026 pass
- [X] T031 [US3] In `src/testset_runner/comparator.py`, populate `retry_policy_a=run_a.retry_policy` and `retry_policy_b=run_b.retry_policy` on `RunComparison`. A policy difference never raises and never affects `_transition`. Make T027 pass
- [X] T032 [US3] Update `src/testset_runner/cli.py`:
  - in `build_parser`, add `run_parser.add_argument("--max-attempts")` (parsed as a string so invalid values get the contract error text, not argparse's)
  - in `_run`, resolve `args.max_attempts or os.environ.get("QA_AGENT_MAX_ATTEMPTS") or "3"`, then validate it as an int ≥ 1, else print `Error: --max-attempts must be an integer >= 1.` to stderr and `return 1` before building the answerer
  - pass `retry_policy=RetryPolicy(max_attempts=n)` to `run_testset`
  - print `Retry policy: max_attempts={p.max_attempts}, waits {p.initial_wait_seconds}s x{p.backoff_multiplier} (cap {p.max_wait_seconds}s)` after the existing summary lines
  - in `_compare`, after each `Run A:`/`Run B:` line, print `  retry policy: <same format>` or `  retry policy: not recorded`
  - update the module docstring's flag list if it enumerates flags

  Make T028 pass.

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, full CI gate, and the manual validation from quickstart.md.

- [X] T033 [P] Review docstrings for Constitution III: `src/qa_agent/failures.py`, `src/qa_agent/transient.py`, `RetryPolicy` (SDK-retry note), and the `run_testset` docstring in `src/testset_runner/runner.py` (retry loop, isolation restated, `sleep` as a test seam, `KeyboardInterrupt` → no partial save). Also update the module docstring of `src/qa_agent/capabilities.py` if it still says failures are discarded
- [X] T034 [P] Verify the layering constraints with `grep -rn "pydantic_ai" src/testset_runner src/qa_agent/failures.py`, which must return nothing
- [X] T035 Run `.venv/bin/pytest` and `.venv/bin/pyright`. Both must pass, and existing `004`/`005` tests must pass unchanged apart from the `test_cli.py` fake signature (T028)
- [X] T036 Run quickstart.md Track 2 manually:
  - **A**: unreachable target with `--api-key sk-test-DO-NOT-LEAK-1234567890`. Expect `Most common failure: ConnectError`, `attempts: 3` everywhere, `grep -r "DO-NOT-LEAK" data/testset_runs/ data/logs/` empty, and 3 run-log lines per question, each with `failure`
  - **C**: `--max-attempts 1` and compare with A
  - **D**: compare a pre-feature run file against a new one

  Record any deviation in `specs/006-agent-error-retry/quickstart.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup. Blocks all user stories (`FailureDetail` is used everywhere).
- **US1 (Phase 3)**: Depends on Foundational.
- **US2 (Phase 4)**: Depends on Foundational. Relies on US1's `describe_failure` (T010) and `failure` plumbing (T011–T013). Implement after US1.
- **US3 (Phase 5)**: Depends on US2's `RetryPolicy` (T022) and `retry_policy` parameter (T024).
- **Polish (Phase 6)**: Depends on all stories.

### User Story Dependencies

- **US1 (P1)**: Standalone MVP. It delivers failure details with single attempts.
- **US2 (P2)**: Builds on US1, whose failure details carry the `transient` flag the retry loop keys on. It remains testable on its own via fake answerers that return `FailureDetail`s directly.
- **US3 (P3)**: Builds on US2's `RetryPolicy`. It adds configuration, persistence, and comparison.

### Within Each User Story

- Tests are written first and fail, then implementation.
- Models (`models.py`) come before logic (`failures.py`/`transient.py`/`runner.py`/`comparator.py`), and logic before CLI.
- Same-file tasks run sequentially: `src/testset_runner/models.py` (T012 → T022 → T023 → T029), `src/testset_runner/runner.py` (T013 → T024 → T030), `src/testset_runner/cli.py` (T014 → T025 → T032), `src/qa_agent/capabilities.py` (T011 → T021).

### Parallel Opportunities

- T002 can run alongside T001.
- US1 tests T005–T009 are all different files and can run in parallel.
- US2 tests T015, T016, T017/T018 and T019 can run in parallel (T018 shares a file with T017, so write them together).
- US3 tests T026, T027 and T028 can run in parallel.
- In US3, T031 (`comparator.py`) can run in parallel with T030 (`runner.py`) once T029 is done.
- T033 and T034 can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Write all US1 tests together (all different files):
Task: "Unit tests for root_cause/redact/truncate/describe_failure in tests/unit/qa_agent/test_failures.py"
Task: "Contract tests for FailureDetail on answer_question in tests/contract/qa_agent/test_failure_details.py"
Task: "Runner failure + errored_by_failure_type tests in tests/contract/testset_runner/test_run_testset.py"
Task: "Pre-006 fixture load test in tests/unit/testset_runner/test_store.py"
Task: "CLI failure-type output tests in tests/unit/testset_runner/test_cli.py"
```

## Parallel Example: User Story 2

```bash
Task: "Classification table in tests/unit/qa_agent/test_transient.py"
Task: "Transient assertions in tests/contract/qa_agent/test_failure_details.py"
Task: "Retry loop + wait tests in tests/contract/testset_runner/test_retry.py"
Task: "Retry summary CLI lines in tests/unit/testset_runner/test_cli.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup → Phase 2 Foundational.
2. Phase 3 (US1): errored questions carry a redacted root-cause type/message in the run file, run log and CLI summary.
3. **STOP and VALIDATE**: `pytest`, then quickstart Track 2 scenario A (expect `attempts` absent and 1 log line per question at this stage).

### Incremental Delivery

1. Setup + Foundational → `FailureDetail` available.
2. + US1 → failure details (MVP).
3. + US2 → bounded retry with the default policy. Match rates stop dropping on transient hiccups.
4. + US3 → `--max-attempts`, persisted policy, and policy shown in comparisons.
5. Polish → docs, CI gate, manual quickstart.

---

## Notes

- [P] = different files, no dependency on incomplete tasks.
- Every persisted-model change is additive and optional, so no migration is needed.
- Commit after each task or logical group, and stop at any checkpoint to validate the story on its own.
