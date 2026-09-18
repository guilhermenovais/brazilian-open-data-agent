# Phase 1 Data Model: Question-Answering Agent Workflow

All boundary-crossing types are `pydantic` v2 models (Engineering Principle 5). Internal
wiring state (`AgentDeps`, `StepBudget`) is plain Python — it never crosses a tool boundary
to the model, so pydantic validation buys nothing there; it's process-internal orchestration
state, injected via `RunContext` (Engineering Principle 4).

## New types (`src/qa_agent/`)

### `AgentAnswer` (models.py) — the `Agent`'s structured `output_type`

The model's own final turn. Portuguese-only content; `outcome` is self-reported by the model
and then possibly overridden deterministically (research.md §5) before it ever reaches a
caller.

| Field     | Type                                | Notes |
|-----------|-------------------------------------|-------|
| `answer`  | `str`                                | Portuguese natural-language final answer text. The only field ever shown to the end user. Never contains file names, column names, or dataset identifiers (FR-003, FR-009). |
| `outcome` | `Literal["full", "partial", "none"]` | Model's own judgment of whether the question was fully answered, partially answered, or not answerable (FR-006/FR-007). Subject to the deterministic clamp in `capabilities.py` (research.md §5) before use. |

**Validation rules**: `answer` must be non-empty (`Field(min_length=1)`) — an empty string is
never a valid final answer, even for the "cannot answer" case (the explanation text itself
is the answer).

### `QuestionAnsweringResult` (models.py) — `answer_question`'s public return type

| Field         | Type                                | Notes |
|---------------|--------------------------------------|-------|
| `answer`      | `str`                                 | Same Portuguese text as `AgentAnswer.answer` (or a fixed fallback message on a Tier 1/3 failure — research.md §10). |
| `dataset_key` | `str`                                  | The key `select_dataset` returned, or a fixed sentinel (`"<none>"`) if dataset selection itself failed (Tier 1). |
| `outcome`     | `Literal["full", "partial", "none"]`    | The final, clamped outcome — identical to what gets written to `AgentRunLogEntry.outcome` for this same call. |

**Relationship**: `answer_question` builds exactly one `QuestionAnsweringResult` per call and
derives exactly one `AgentRunLogEntry` from it (plus the question and a fresh timestamp)
before returning — the two are always in lockstep, never constructed independently in two
different places, so they can't drift apart (research.md §9).

### `AgentRunLogEntry` (models.py) — FR-013's usage/research record

Field-for-field the same shape the spec's Key Entities section defines for "Agent Run Log
Entry," deliberately mirroring `dataset_selector.models.DatasetSelectionLogEntry`'s existing
shape and role.

| Field         | Type       | Notes |
|---------------|------------|-------|
| `question`    | `str`       | The original Portuguese question, verbatim. |
| `dataset_key` | `str`        | Same value as `QuestionAnsweringResult.dataset_key`. |
| `outcome`     | `Literal["full", "partial", "none"]` | Same (clamped) value as `QuestionAnsweringResult.outcome`. |
| `timestamp`   | `datetime`    | UTC, set by `answer_question` at the moment the final answer (of any kind) is produced — same convention as `DatasetSelectionLogEntry.timestamp`. |

### `BudgetExhausted` (step_budget.py) — the tool-wrapper result once the 10-step bound is hit

A validated pydantic model rather than a bare string, so it crosses the tool boundary the
same way every other tool result does (Engineering Principle 5), even though it carries no
domain data.

| Field     | Type  | Notes |
|-----------|-------|-------|
| `message` | `str`  | Fixed Portuguese text instructing the model to finalize its answer now using whatever was already retrieved (research.md §3). Not user-facing — this is what the *model* sees as this tool call's result, not the final answer. |

### `StepBudget` (step_budget.py) — plain class, not a pydantic model

Lives in `AgentDeps`, mutated by the four tool wrappers. Not validated at any boundary
because it never crosses one — it's pure in-process orchestration state.

| Attribute   | Type  | Notes |
|-------------|-------|-------|
| `limit`     | `int`  | Fixed at `10` (`RETRIEVAL_STEP_LIMIT` module constant — FR-012, not caller-configurable per spec Assumptions). |
| `attempts`  | `int`   | Incremented by a tool wrapper before it does any work, every call (whether it goes on to succeed, raise `ModelRetry`, or hit the limit itself — research.md §3). |
| `successes` | `int`    | Incremented only when the wrapped `data_access` capability call actually returns a result without raising. Read by `capabilities.py`'s outcome clamp (research.md §5): `successes == 0` ⇒ forced `outcome="none"`. |

**Methods**: `try_reserve() -> bool` — returns `True` and increments `attempts` if
`attempts < limit`, else returns `False` and leaves `attempts` unchanged (so a wrapper can
tell "may I proceed" from "budget exhausted" without special-casing off-by-one arithmetic
itself); `record_success() -> None` — increments `successes`.

### `AgentDeps` (deps.py) — `RunContext[AgentDeps]`, plain dataclass

Constructed once per `answer_question` call, after dataset selection succeeds, before the
`Agent` is run.

| Field         | Type          | Notes |
|---------------|---------------|-------|
| `dataset`     | `data_access.dataset.Dataset` | The one selected dataset's handle — reused as-is from `DatasetSelectionResult.dataset` (`002`). Every tool wrapper calls `data_access.capabilities.*(ctx.deps.dataset, ...)` against this same instance. |
| `dataset_key` | `str`          | For logging/traceability only; tool wrappers don't need it. |
| `step_budget` | `StepBudget`    | Mutable, shared across every tool call within this one run. |

### `AgentSettings` (settings.py) — `pydantic_settings.BaseSettings`

The first typed settings object in this codebase (Engineering Principle 7), env-prefixed
`QA_AGENT_`.

| Field        | Type   | Default    | Notes |
|--------------|--------|------------|-------|
| `model_name` | `str`   | *(required, no default)* | `pydantic-ai` model identifier string (e.g. `"openai:gpt-4o-mini"`), env var `QA_AGENT_MODEL`. Every run's exact model must be explicit (research.md §6). |
| `instrument` | `bool`   | `True`      | Passed to `Agent(instrument=...)` — enables native OpenTelemetry spans (research.md §8), env var `QA_AGENT_INSTRUMENT`. |

## Reused types (unchanged)

From `002-dataset-selector`:

- `DatasetSelectionResult` (`dataset_key`, `briefing`, `dataset`) — consumed once by
  `answer_question` at the start of every call.
- `select_dataset(question, selector, logger)` and its own `DatasetSelectionLogEntry` /
  `JsonlSelectionLogger` — untouched; this feature's `RunLogger`/`JsonlRunLogger` (§ above)
  is a separate, additional log, not a replacement.
- `dataset_selector.exceptions.*` (`NoBriefingsAvailableError`, `DatasetNotFoundError`,
  `BriefingNotFoundError`) — caught by `answer_question` as Tier 1 failures (research.md
  §10).

From `001-data-access-tools`:

- `DiscoveryResult`, `SchemaInspectionResult`, `FieldInfo`, `RowQueryResult`,
  `FilterCondition` (`EqualsCondition`/`ContainsCondition`/`RangeCondition`),
  `AggregationRequest`, `AggregateSpec`, `AggregationResult`, `AggregationGroup` — used
  directly, unmodified, as the four tool wrappers' own input/output schemas. No parallel
  "agent-facing" copies of these models are created.
- `data_access.capabilities.{discover_data_sources, inspect_schema, query_rows,
  aggregate_rows}` — called by the tool wrappers exactly as documented in
  `001-data-access-tools/contracts/`.
- `data_access.exceptions.DataAccessError` and its five subclasses — caught by the tool
  wrappers and translated to `pydantic_ai.ModelRetry` (research.md §4).

## State / control flow (not a database — a single request's lifecycle)

```text
answer_question(question)
  │
  ├─ 1. select_dataset(question, ...)              [dataset_selector, unmodified]
  │      ├─ raises DatasetSelector* error  ──────►  Tier 1 fallback AgentAnswer(outcome="none")
  │      └─ returns DatasetSelectionResult
  │
  ├─ 2. build AgentDeps(dataset, dataset_key, StepBudget(limit=10))
  ├─ 3. render system prompt from prompts/system_v1.md + briefing
  ├─ 4. agent_factory.build_agent(settings) → Agent[AgentDeps, AgentAnswer]
  │
  ├─ 5. agent.run(question, deps=..., ...)
  │      │  (0..10 tool calls, each: try_reserve() → BudgetExhausted if False,
  │      │   else call data_access capability → ModelRetry on DataAccessError,
  │      │   else record_success() + return the capability's own result model)
  │      ├─ raises (UnexpectedModelBehavior / provider error / other)
  │      │        ──────────────────────────────────►  Tier 3 fallback AgentAnswer(outcome="none")
  │      └─ returns AgentAnswer{answer, outcome}
  │
  ├─ 6. clamp: if step_budget.successes == 0 → outcome = "none"   [research.md §5]
  ├─ 7. write AgentRunLogEntry(question, dataset_key, outcome, now())  [always, every path]
  └─ 8. return QuestionAnsweringResult(answer, dataset_key, outcome)
```
