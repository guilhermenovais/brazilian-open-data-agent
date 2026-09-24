# Research: Agent Error Details and Bounded Retry

**Feature**: `006-agent-error-retry` | **Date**: 2026-09-24 | **Spec**: [spec.md](./spec.md)

Every decision below cites the spec requirement it serves. Facts about third-party behavior were
checked against the installed versions (`pydantic-ai` 2.45.0, `openai` 3.15.0) in `.venv`, not
assumed.

---

## §1 Where the retry loop lives: in `testset_runner`, around the `QuestionAnswerer` seam

**Decision**: The bounded retry loop lives in `testset_runner.runner.run_testset`. It calls
`answerer.answer(question)` again, up to `RetryPolicy.max_attempts` times, while the returned
`QuestionAnsweringResult.failure` is transient. `qa_agent` makes a single attempt per
`answer()` call. It never retries on its own; it only *describes* and *classifies* the failure.

**Rationale**:
- **Isolation (FR-015)**: every `answer()` call already builds a fresh `Agent`, `AgentDeps` and
  `StepBudget` (the `004` isolation guarantee). A retry that is just "call `answer()` again"
  inherits that guarantee as-is: no conversation, partial steps or budget state can leak from
  a failed attempt. Graded steps are those of the successful attempt (FR-016) because the
  runner only keeps the last result.
- **Policy is a run concept (FR-020, FR-022, FR-023)**: the policy is set per run, persisted
  with the run and compared between runs. `TestRun` already owns run conditions, so the policy
  belongs there too.
- **Web UI unchanged (spec Assumptions, FR-009)**: the chat UI shares `QaAgentQuestionAnswerer`.
  A retry inside `qa_agent` would silently change the chat's latency and behavior, which the
  spec puts out of scope. A retry in the runner leaves the chat untouched, and the chat still
  gets failure details in the run log (FR-008).
- **Eng. Principle 1**: `testset_runner` keeps its rule of never importing `pydantic_ai`. It
  sees only `FailureDetail.transient` and `FailureDetail.retry_after_seconds`, which are plain
  data.

**Alternatives considered**:
- *Retry inside `_answer_with_selection` around `agent.run_sync`*: it would also cover the web
  UI (out of scope), and the policy would then need to be threaded through
  `QaAgentQuestionAnswerer` into `AgentSettings`, mixing a run-level concern into agent
  construction. Rejected.
- *Retry at the HTTP transport (`pydantic_ai.retries.HTTPX2TenacityTransport`)*: this retries
  individual model requests *mid-conversation*, not whole questions. The spec's assumption says
  a retry "re-asks the whole question from scratch". A transport-level retry also only works
  for providers whose HTTP client we build ourselves. Today that is only the `base_url` path in
  `agent_factory.py`, not the `"openai:..."` model-string path. Rejected.
- *Tenacity decorator in the runner*: `tenacity` is installed transitively, but the loop is
  about 15 lines. A decorator would hide the per-attempt bookkeeping that FR-018 requires us to
  record, and would add a direct dependency for something trivial. Rejected (Principle VII).

---

## §2 Interaction with the OpenAI SDK's own built-in request retries

**Finding**: `openai` 3.15.0 retries each HTTP request by itself by default
(`DEFAULT_MAX_RETRIES = 2` in `openai/_constants.py`). It retries on connection errors, 408,
409, 429 and 5xx, honors `Retry-After`, and has a default timeout of 600 s. These retries
happen *inside* one model request and keep the conversation intact. `pydantic-ai` only sees the
final failure, which it wraps as `ModelHTTPError` / `ModelAPIError`.

**Decision**: Leave the SDK's request-level retries unchanged. Document that one question
*attempt* (what this feature counts, records and bounds) may internally include up to 3 HTTP
tries of each model request. Record this in the `RetryPolicy` docstring and the quickstart so a
reviewer does not read `attempts=1` as "exactly one HTTP request".

**Rationale**: Turning SDK retries off consistently would require building every provider
client ourselves, including the `"provider:model"` string path that `pydantic-ai` resolves
internally. That is provider-specific code in the core (Principle V) for a behavior the spec
does not ask to change. The two layers do not conflict: the SDK absorbs sub-second hiccups
mid-conversation, and the question-level retry catches what is left. Whether the SDK retries
should also be recorded or configurable can be raised later if a run shows it matters
(Principle II).

**Alternatives considered**: `max_retries=0` only on the `base_url` path. Rejected because the
two target kinds would then have different, invisible retry semantics, which is worse for
comparability than one documented behavior.

---

## §3 Transient vs. non-transient classification rules

**Decision**: A failure is **transient** if *any* exception in its cause chain matches one of
these rules. Otherwise it is **non-transient** (FR-011: unknown means non-transient).

| Rule | Covers (FR-010) |
|------|-----------------|
| `pydantic_ai.exceptions.ModelHTTPError` with `status_code` in {408, 425, 429} or 500–599 except 501 | request timeout, rate limit, temporary server error (incl. 529 "overloaded" used by some providers) |
| `pydantic_ai.exceptions.ModelAPIError` that is **not** a `ModelHTTPError` | connection failures and timeouts. `pydantic-ai` maps the provider SDK's connection/timeout errors to a plain `ModelAPIError` (`models/openai.py` `_map_api_errors`). The only other in-tree use is "streamed response ended without a finish_reason", which is also a truncated-transport symptom and safe to retry. |
| built-in `TimeoutError`, `ConnectionError` (and subclasses) | timeouts/connection failures from any provider that does not wrap them |

Everything else is non-transient, including:
- `ModelHTTPError` 400/401/403/404/422: invalid request, auth rejected, unknown model.
- `UnexpectedModelBehavior` (output-validation retries exhausted, content filter) and
  `UsageLimitExceeded`: agent behavior outcomes, per the spec's edge cases.
- Dataset-selection failures. They never reach the classifier and are built directly with
  `transient=False` (FR-010).

**Rationale**:
- Rules key only on `pydantic-ai`'s provider-neutral exception hierarchy plus the standard
  library. No provider SDK type (`openai.RateLimitError`, `httpx.ConnectError`) is named, so
  the rules generalize to any provider `pydantic-ai` supports (Principle V).
- "Any link in the chain" satisfies the edge case "a failure wraps another failure… the
  transient/non-transient decision reflects the real cause". For example, an
  `UnexpectedModelBehavior` raised *from* a `TimeoutError` is transient.
- A deterministic rule table, not model judgment (Principle VI).

**Alternatives considered**:
- *Matching the root cause only*: the root is often a provider-SDK or `httpx` type (e.g.
  `openai.RateLimitError`) that we do not want to name. The `pydantic-ai` wrapper that carries
  `status_code` is one level up. Rejected.
- *Treating every `ModelAPIError` as transient*: this would retry 401/404, contradicting
  FR-013. Rejected.
- *Retrying 409*: the OpenAI SDK retries it at request level, but it signals a state conflict,
  not transient load. Left out, and still covered by §2's inner layer.

The rules live in a small `pydantic-ai`-aware module (`qa_agent/transient.py`). The
framework-agnostic parts (chain walking, redaction, truncation, building a `FailureDetail`)
live in `qa_agent/failures.py` with no `pydantic_ai` import (Eng. Principle 1).

---

## §4 Which exception's type and message to record (FR-004)

**Decision**: Walk the cause chain from the caught exception: follow `__cause__`, else
`__context__` unless `__suppress_context__` is set. Stop at the end or on a cycle. Record the
**root** (last) exception's class name (`type(exc).__name__`) and `str(exc)`.

**Rationale**: this is what the spec's edge case asks for. It also produces the most useful
labels for the per-type summary (FR-007). Checked against the installed stack:
- rate limit → `ModelHTTPError` ← `openai.RateLimitError`: recorded `RateLimitError`,
  `"Error code: 429 - {...}"`
- auth → `ModelHTTPError` ← `openai.AuthenticationError`: recorded `AuthenticationError`
- timeout → `ModelAPIError` ← `openai.APITimeoutError` ← `httpx2.ReadTimeout`: recorded
  `ReadTimeout`
- refused connection → `ModelAPIError` ← `openai.APIConnectionError` ← `httpx2.ConnectError`:
  recorded `ConnectError`, `"[Errno 111] Connection refused"`

The class name alone (not `module.qualname`) is used because it is readable in a report and
stable across private-module moves (e.g. `openai._exceptions`). Collisions between two
different classes with the same name are harmless for a review aid.

**Alternatives considered**: recording the outermost exception (`ModelHTTPError`) only: every
HTTP failure would collapse into one summary bucket. Recording the full chain: extra report
bulk, and the spec does not ask for it. Rejected.

---

## §5 Credential redaction (FR-005, SC-004, Principle VIII)

**Decision**: `redact(message, secrets)` runs before truncation and before anything is logged
or persisted, in two passes:
1. **Exact-value pass**: every non-empty configured secret (`AgentSettings.api_key`) is
   replaced with `[REDACTED]`. This guarantees SC-004 ("no credential *supplied to the run*").
2. **Pattern pass** for credentials we were not handed directly (e.g. `OPENAI_API_KEY` read by
   the provider SDK itself, or a provider echoing a token): `Bearer <token>`, `sk-…`-style keys
   (≥ 16 chars after the prefix), and `api_key` / `api-key` / `apikey` / `token` /
   `authorization` / `key` followed by `=` or `:` and a value. Each match is replaced with
   `[REDACTED]`.

**Rationale**: the exact-value pass is the guarantee. The pattern pass is a best-effort safety
net that stays generic (not keyed to one provider's key format beyond the widespread `sk-`
prefix).

**Order matters**: redact → truncate. Truncating first could cut a key in half, and the exact
pass would then miss the leftover prefix.

**Alternatives considered**: pattern-only (cannot guarantee SC-004 for arbitrary key formats,
rejected); dropping messages whenever they look sensitive (defeats FR-001, rejected).

---

## §6 Message length cap (FR-006)

**Decision**: Cap recorded messages at **2,000 characters**. A longer message keeps its first
2,000 characters followed by `… [truncated N characters]`. An empty message is recorded as `""`
(edge case: never omitted or replaced with a placeholder).

**Rationale**: 2,000 characters fits a full JSON error body from the major providers (typically
200–800 characters) while bounding a pathological HTML error page. It is a constant in
`failures.py`, not a setting, because no requirement asks to vary it (Principle VII).

---

## §7 Wait schedule between attempts (FR-014)

**Decision**: `RetryPolicy` defaults: `max_attempts=3`, `initial_wait_seconds=2.0`,
`backoff_multiplier=2.0`, `max_wait_seconds=60.0`. The wait before retry *k* (k = 1, 2, …) is:

```text
backoff  = initial_wait_seconds × backoff_multiplier^(k-1)       # 2 s, 4 s, 8 s, …
wait     = max(backoff, retry_after_seconds or 0)
wait     = min(wait, max_wait_seconds)
```

`retry_after_seconds` comes from `ModelHTTPError.retry_after`, which `pydantic-ai` already
parses from the `Retry-After` header (both delta-seconds and HTTP-date). It is the first
`ModelHTTPError` in the chain that carries one.

**Rationale**: "wait increasing on successive retries" plus "respect the provider's indication,
subject to an upper bound" (FR-014). A suggested delay shorter than our backoff does not shorten
the backoff. With the defaults, a fully unreachable target costs at most 2 + 4 = 6 s of waiting
per question on top of the attempts themselves, or ≤ 120 s when a `Retry-After` is honored
(SC-005).

**No jitter**: jitter protects many concurrent clients from synchronized retries. This runner is
one sequential client, and deterministic waits make runs easier to reason about and to test.

**Injectable sleep**: `run_testset` takes `sleep: Callable[[float], None] = time.sleep` so tests
assert the exact wait sequence without real sleeping (Principle IV).

**Interruption**: a `KeyboardInterrupt` during `sleep` propagates out of `run_testset` before
`store.save`, so no partial run is ever persisted. This is the existing interrupted-run
behavior (spec edge case), and nothing new is required.

---

## §8 Configuration surface (FR-020, FR-021)

**Decision**: Add a `--max-attempts N` flag to `testset_runner run`, with a `QA_AGENT_MAX_ATTEMPTS`
environment-variable fallback (matches the existing CLI convention that every flag has a
`QA_AGENT_*` fallback), and default 3. Values < 1 are rejected with an error before the run
starts. `1` disables retries. The wait parameters are **not** exposed. They keep their
defaults, but are recorded in the persisted `RetryPolicy` so a future change to the defaults
stays visible in old versus new runs (FR-022).

**Rationale**: FR-020 asks only for the maximum attempts to be settable. Exposing wait tuning
would be unrequested generality (Principle VII). `RetryPolicy` is a pydantic model, so the whole
policy is one explicit, recorded settings object (Eng. Principle 7).

---

## §9 Backward compatibility of persisted runs (FR-024, SC-006)

**Decision**: every new persisted field is optional with a `None` default meaning "not
recorded": `TestRun.retry_policy`, `QuestionResult.attempts` / `failure`, and the three new
`RunSummary` figures. `QuestionResult.failed_attempts` defaults to `[]`, and whether it was
recorded is read from `attempts is None`. The CLI prints `not recorded` for `None`. No
migration, no schema version field.

**Rationale**: `JsonFileRunStore.load` is plain `TestRun.model_validate_json`. Optional
defaults let any pre-feature file validate unchanged, which is verified by a fixture copied
from a real pre-feature run shape. A schema-version field would be unused generality until a
non-additive change happens.

---

## §10 Run-log extension (FR-008)

**Decision**: `AgentRunLogEntry` gains `failure: FailureDetail | None = None`. One entry is
still written per `answer_question` call, so a retried question naturally produces one log
line per attempt. That is the right granularity for usage-as-research-data (Principle X):
the log shows every attempt that actually happened, including those in chat sessions.

---

## §11 Testing approach

- **`qa_agent` contract tests** (`FunctionModel` raising real `pydantic_ai.exceptions` instances):
  429 with `retry-after`, 503, 401, 404, plain `ModelAPIError`, `TimeoutError` wrapped in a
  `RuntimeError`, an unknown `ValueError`, a message echoing the configured API key, and a
  dataset-selection failure. Each asserts the returned `FailureDetail`, the run-log line, and
  that `answer` text is unchanged (FR-009).
- **`qa_agent` unit tests** for `failures.py`: chain walking (cause, context, suppressed context,
  cycle), redaction (exact and pattern), truncation marker, empty message.
- **`testset_runner` contract tests** with a scripted fake answerer (a failure sequence per
  question) and a recording fake `sleep`. They map 1:1 to US2/US3 acceptance scenarios and
  SC-002/SC-003, and cover the wait sequence, `Retry-After` honoring and capping, and
  `max_attempts=1`.
- **Store/comparator unit tests**: a pre-feature run fixture loads and compares, with
  `retry_policy` present on one side only.
- **CLI unit test**: `--max-attempts` / `QA_AGENT_MAX_ATTEMPTS` wiring and rejection of `0`.

No live-model test is needed. Every behavior here is deterministic given a scripted failure
sequence.
