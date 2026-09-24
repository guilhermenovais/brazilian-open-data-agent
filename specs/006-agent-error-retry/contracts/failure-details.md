# Contract: Failure Details from `qa_agent`

This is a change to `answer_question` (contract: `specs/003-qa-agent-workflow/contracts/answering.md`)
and to its seam `QuestionAnswerer.answer` (`src/qa_agent/answerer.py`). The signatures stay the
same. Only the returned and logged data grow.

```python
def answer_question(question, *, selector, selection_logger, run_logger, settings) -> QuestionAnsweringResult
```

## Still never raises

Everything that was caught before is still caught. The existing fixed Portuguese answer texts are
unchanged (FR-009). What changes is that each caught failure now also produces a `FailureDetail`
(data-model.md):

| Failure path | `errored` | `failure.type` | `failure.transient` |
|--------------|-----------|----------------|---------------------|
| Dataset selection raises `NoBriefingsAvailableError` / `DatasetNotFoundError` / `BriefingNotFoundError` | `True` | that exception's class name | `False` |
| `agent.run_sync` raises any `Exception` | `True` | root-cause class name (research.md §4) | per research.md §3 rules |
| Normal completion (any `outcome`, including step-budget exhaustion) | `False` | *(`failure is None`)* | — |

## Framework-agnostic helpers (`qa_agent/failures.py`, no `pydantic_ai` import)

```python
def root_cause(exc: BaseException) -> BaseException: ...
def redact(message: str, secrets: Iterable[str | None]) -> str: ...
def truncate(message: str, limit: int = MAX_MESSAGE_CHARS) -> str: ...
def describe_failure(
    exc: BaseException,
    *,
    secrets: Iterable[str | None],
    classify: Callable[[BaseException], TransientVerdict],
) -> FailureDetail: ...
```

- `describe_failure` works in this order: root cause → `redact` → `truncate`. It sets
  `transient` / `retry_after_seconds` from `classify(exc)`, where `exc` is the whole chain and
  not just the root.
- `redact` always removes every non-empty value in `secrets` exactly, then applies the generic
  credential patterns (research.md §5).

## `pydantic-ai`-aware classification (`qa_agent/transient.py`)

```python
class TransientVerdict(NamedTuple):
    transient: bool
    retry_after_seconds: float | None

def classify(exc: BaseException) -> TransientVerdict: ...
```

- Applies the research.md §3 rule table to every link in the chain.
- Anything unrecognized returns `TransientVerdict(False, None)` (FR-011).

## Credential guarantee (FR-005, SC-004)

The `QaAgentQuestionAnswerer` passes `settings.api_key` as a secret. No `FailureDetail` returned
or logged by `answer_question` contains that value, whatever the provider echoes back.

## Run log (FR-008)

Each `answer_question` call writes exactly one `AgentRunLogEntry`, as before. It now includes
`failure`, which is the same object returned on the result.

## Behavioral requirements (traceability)

| Requirement | Behavior |
|-------------|----------|
| FR-001/FR-003 | Both failure paths populate `failure`. |
| FR-004 | `failure.type` and `failure.message` come from the root of the cause chain. |
| FR-005 | `failure.message` is redacted before it is returned or logged. |
| FR-006 | `failure.message` is at most 2,000 characters plus the truncation marker. |
| FR-008 | `AgentRunLogEntry.failure` is populated. |
| FR-009 | `answer` text is identical to the pre-feature text for every path. |
| FR-010/FR-011 | `failure.transient` is set per research.md §3. Unknown → `False`. |
