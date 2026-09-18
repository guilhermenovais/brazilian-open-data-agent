# Phase 1 Data Model: Testset Runner for LLM Evaluation

All boundary-crossing types are `pydantic` v2 models (Engineering Principle 5). Protocol seams
(`QuestionAnswerer`, `MatchStrategy`) are plain Python `Protocol`s — they exist for dependency
injection (Engineering Principle 4) and future extensibility (Engineering Principle 2), not for
validation.

## Extended types (`src/qa_agent/`) — additive, backward compatible with `003`

### `RetrievalStep` (models.py) — **new**

One entry per tool call/return pair pulled from `run_result.all_messages()` after a successful
`agent.run_sync` call.

| Field            | Type  | Notes |
|------------------|-------|-------|
| `tool_name`      | `str`  | e.g. `"aggregate_rows"` — the `@agent.tool` function name invoked. |
| `arguments`      | `dict` | The tool call's arguments, as the model supplied them (already validated pydantic input, dumped to a plain dict for storage — FR-005's "steps the agent took"). |
| `result_summary` | `str`  | `str(result)` for a plain value, or `result.model_dump_json()` truncated/summarized for a pydantic result (e.g. `RowQueryResult`, `BudgetExhausted`) — enough for a person reading a run report to see what the tool returned without re-running anything (SC-002). |

### `QuestionAnsweringResult` (models.py) — **two new fields added**

| Field         | Type                                  | Notes |
|---------------|----------------------------------------|-------|
| `answer`      | `str`                                    | Unchanged from `003`. |
| `dataset_key` | `str`                                      | Unchanged from `003`. |
| `outcome`     | `Literal["full", "partial", "none"]`        | Unchanged from `003`. |
| `steps`       | `list[RetrievalStep]` (default `[]`)         | **New.** Populated only on the path that reaches a real `agent.run_sync` call; empty on both Tier 1 (no dataset) and Tier 3 (crashed before/without a real run) failure paths, since there is nothing to report there. |
| `errored`     | `bool` (default `False`)                      | **New.** `True` on both existing `except` branches in `capabilities.py` (Tier 1 dataset-selection failure, Tier 3 catastrophic model-call failure); `False` on every path that produced a real `AgentAnswer`, including a legitimate `outcome="none"` where the model itself concluded it couldn't answer. This is the signal `testset_runner` needs to tell "the agent looked and found nothing" apart from "something broke," which `outcome` alone cannot express (research.md §3). |

**Backward compatibility**: no existing `003` contract test constructs `QuestionAnsweringResult`
directly for equality comparison (verified against the current test suite); both new fields
have defaults, so every existing call site and assertion (`result.answer`, `result.outcome`,
`result.dataset_key`) is unaffected.

### `AgentSettings` (settings.py) — **two new optional fields added**

| Field        | Type          | Default | Notes |
|--------------|----------------|---------|-------|
| `model_name` | `str`           | *(required)* | Unchanged from `003`. When `base_url` is set, this is a bare model id for that endpoint (e.g. `"gpt-4o-mini"`, not `"openai:gpt-4o-mini"`) — the `openai:` prefix form is `pydantic-ai`'s own inference-string convention for its *default*-hosted providers and is bypassed once a custom `base_url`/`Provider` is constructed explicitly. |
| `instrument` | `bool`           | `True`   | Unchanged from `003`. |
| `base_url`   | `str \| None`     | `None`   | **New.** Env `QA_AGENT_BASE_URL`. When set, `agent_factory.build_agent` constructs an explicit `OpenAIChatModel(model_name, provider=OpenAIProvider(base_url=..., api_key=...))` instead of passing `model_name` as a bare inference string (research.md §4). |
| `api_key`    | `str \| None`     | `None`   | **New.** Env `QA_AGENT_API_KEY`. Passed to `OpenAIProvider` only when `base_url` is set; ignored otherwise (the default path still relies on the provider SDK's own standard env var, e.g. `OPENAI_API_KEY`, per Constitution Principle VIII — unchanged from `003`). |

## New types (`src/testset_runner/`)

### `Question` (models.py)

Field-for-field the bundled testset's own schema (`data/testsets/orcamentos-aeb-csv.json`).

| Field      | Type  | Notes |
|------------|-------|-------|
| `n`        | `int`  | The testset's own question identifier — used, not regenerated, so a person can cross-reference a report row against the source file (`Field(gt=0)`). |
| `type`     | `str`   | Category, e.g. `"single-lookup"`, `"calculation"`, `"multiple-files"`, `"edge-cases"` — free-text, not a closed `Literal`, so a future testset can introduce new categories without a code change (FR-001's "structured like the bundled sample," not "identical categories to it"). |
| `question` | `str`    | Portuguese question text (`Field(min_length=1)`). |
| `expected` | `str`     | Expected answer, always textual in the source file even when numeric (`Field(min_length=1)`). |
| `source`   | `str`      | Reference to where the answer comes from (e.g. `"dados_gerais/tb_geral.csv"`); free text, not validated against the actual dataset — this feature does not re-verify the testset author's own citations. |

**Validation rule**: FR-013 requires the whole testset to fail fast if *any* record is missing
`question` or `expected` — `Question`'s own `Field(min_length=1)` constraints make a single
`pydantic.ValidationError` during testset loading do exactly that; `TestsetLoader` does not
catch and skip individual bad records.

### `Testset` (models.py)

| Field           | Type              | Notes |
|-----------------|-------------------|-------|
| `path`          | `str`               | The file path it was loaded from, as given. |
| `content_hash`  | `str`                | SHA-256 hex digest of the file's raw bytes, computed once at load time (research.md §7/§8) — the identity FR-011 and comparison actually key on, not `path`. |
| `questions`     | `list[Question]`      | Order preserved from the source file; duplicate question *text* across two entries is allowed and each is still reported as its own independent row (Edge Cases) — uniqueness is only ever enforced on `n`. |

**Validation rule**: `n` values must be unique within one `Testset` (`TestsetLoader` raises
`TestsetLoadError` otherwise) — needed because `RunComparison` (§ below) joins two runs'
`QuestionResult`s by `n`.

### `TargetConfiguration` (models.py)

| Field        | Type          | Notes |
|--------------|----------------|-------|
| `model_name` | `str`           | Same value passed into `AgentSettings.model_name` for this run. |
| `base_url`   | `str \| None`     | Same value passed into `AgentSettings.base_url`, or `None`. Recorded so a persisted run states plainly which endpoint it hit (US3 AS2). |

**Never includes**: an API key or any other credential — Constitution Principle VIII. This is
the one piece of `AgentSettings` that is safe, and useful, to persist verbatim inside a
`TestRun`; `api_key` has no field here at all, by design, not merely left unset.

### `RetrievalStepView` — reused as-is

`testset_runner` stores `qa_agent.models.RetrievalStep` objects directly inside each
`QuestionResult` — no parallel "testset-runner's own copy" of this shape is created (Principle V
— don't re-encode a fact `qa_agent` already owns).

### `QuestionResult` (models.py)

The outcome of asking one `Question` within one `TestRun`.

| Field            | Type                                                          | Notes |
|------------------|----------------------------------------------------------------|-------|
| `n`              | `int`                                                            | Same as the source `Question.n`. |
| `question`       | `str`                                                             | Copied from `Question.question`, so a report row is self-contained without re-opening the testset file. |
| `expected`       | `str`                                                              | Copied from `Question.expected`. |
| `category`       | `str`                                                                | Copied from `Question.type`. |
| `actual_answer`  | `str`                                                                 | `QuestionAnsweringResult.answer`. |
| `agent_outcome`  | `Literal["full", "partial", "none"]`                                   | `QuestionAnsweringResult.outcome` — the agent's own self-reported outcome, kept distinct from `match_status` below (FR-005 lists them as two separate things to capture). |
| `dataset_key`    | `str`                                                                    | `QuestionAnsweringResult.dataset_key`. |
| `steps`          | `list[qa_agent.models.RetrievalStep]`                                     | `QuestionAnsweringResult.steps`, stored verbatim. |
| `match_status`   | `Literal["matched", "not_matched", "needs_review", "errored"]`             | `"errored"` when `QuestionAnsweringResult.errored` is `True` (research.md §3); otherwise the `MatchStrategy` verdict (research.md §5) — `NumericMatchStrategy`'s `"matched"`/`"not_matched"`, or `"needs_review"` for any non-numeric `expected`. |

**Validation rule**: `match_status == "errored"` if and only if the underlying
`QuestionAnsweringResult.errored` was `True` — the matcher is never even invoked in that case
(there is no trustworthy `actual_answer` to grade).

### `RunSummary` (models.py)

| Field                | Type                       | Notes |
|----------------------|----------------------------|-------|
| `total_questions`    | `int`                       | `len(testset.questions)`. |
| `match_rate`         | `float`                      | `matched / total_questions` — `not_matched`/`needs_review`/`errored` all count as non-matches in this single headline number (FR-008); the per-category breakdown below is where a person sees *why*. |
| `by_status`          | `dict[str, int]`              | Counts per `match_status` value, across the whole run. |
| `by_category`        | `dict[str, RunSummary]` \*      | Per-`category` (Question.type) breakdown of the same counts/rate, so a person can see which categories are underperforming without reading every row (SC-005). \*Recursive in shape only — nested entries omit their own `by_category`. |
| `target_unreachable` | `bool`                        | Set by the run-level heuristic (research.md §6). When `True`, the summary's rendered text leads with this instead of the raw match rate, since the rate is meaningless in that case. |

### `TestRun` (models.py)

One execution of a `Testset` against a `TargetConfiguration`.

| Field       | Type                       | Notes |
|-------------|----------------------------|-------|
| `run_id`    | `str`                       | Filesystem-safe timestamp-based identifier (research.md §7), also the saved file's basename. |
| `created_at`| `datetime`                   | UTC, set when the run starts. |
| `testset`   | `Testset`                     | The full `Testset` used — including `content_hash`, so a saved run is self-describing without needing the original file to still exist unchanged on disk. |
| `target`    | `TargetConfiguration`           | Model/URL used for this run (FR-002, FR-011). |
| `results`   | `list[QuestionResult]`            | One per `Question`, same order as `testset.questions`. |
| `summary`   | `RunSummary`                       | Derived from `results` — never edited independently of them (mirrors `003`'s "the two are always in lockstep" pattern for `QuestionAnsweringResult`/`AgentRunLogEntry`). |

### `ComparisonEntry` (models.py)

| Field        | Type                                                                                                     | Notes |
|--------------|-----------------------------------------------------------------------------------------------------------|-------|
| `n`          | `int`                                                                                                        | Joins `run_a`'s and `run_b`'s `QuestionResult`s. |
| `question`   | `str`                                                                                                         | For display; taken from `run_a` (identical to `run_b`'s once `content_hash` is confirmed equal). |
| `status_a`   | `Literal["matched", "not_matched", "needs_review", "errored"]`                                                 | `run_a`'s `match_status` for this question. |
| `status_b`   | `Literal["matched", "not_matched", "needs_review", "errored"]`                                                  | `run_b`'s `match_status` for this question. |
| `transition` | `Literal["newly_passing", "newly_failing", "still_passing", "still_failing", "unchanged_other"]`                 | Derived: `matched→matched` = `still_passing`; `not-matched-family→matched` = `newly_passing`; `matched→not-matched-family` = `newly_failing`; `not-matched-family→not-matched-family` (same or different member) = `still_failing`; any pair involving `needs_review`/`errored` on both sides with no matched/not_matched crossing = `unchanged_other` if `status_a == status_b`, else counted under the crossing rule above (a `needs_review→not_matched` transition, for instance, is `still_failing`; a `needs_review→matched` transition is `newly_passing`). |

### `RunComparison` (models.py)

| Field       | Type                            | Notes |
|-------------|----------------------------------|-------|
| `run_a`     | `TargetConfiguration`             | Which model/URL `run_a` used (FR-010 AS2). |
| `run_b`     | `TargetConfiguration`              | Which model/URL `run_b` used. |
| `entries`   | `list[ComparisonEntry]`             | One per question, always `== testset.questions` length — never just the changed subset (research.md §8, SC-003). |
| `summary`   | `dict[str, int]`                     | Counts per `transition` bucket; keys' values always sum to `len(entries)`. |

## Protocol seams (`src/testset_runner/`) — plain Python, not pydantic

### `QuestionAnswerer` (question_answerer.py)

```python
class QuestionAnswerer(Protocol):
    def answer(self, question: str) -> QuestionAnsweringResult: ...
```

One concrete implementation ships now: `QaAgentQuestionAnswerer`, a thin adapter that closes
over a `DatasetSelector`, loggers, and an `AgentSettings` (all built once per run from the
CLI's `TargetConfiguration`) and calls `qa_agent.capabilities.answer_question` per `.answer()`
call. Tests substitute a scripted fake (research.md §10).

### `MatchStrategy` (matcher.py)

```python
class MatchStrategy(Protocol):
    def evaluate(self, expected: str, actual_answer: str) -> Literal["matched", "not_matched", "needs_review"]: ...
```

One concrete implementation ships now: `NumericMatchStrategy` (research.md §5), wrapped by
`DeterministicMatcher.grade(...)` which is what `runner.py` actually calls.

## State / control flow

```text
run_testset(testset_path, target_config)
  │
  ├─ 1. TestsetLoader.load(testset_path)             → Testset | raises TestsetLoadError
  │      (missing file / unreadable / any record missing question|expected|n-uniqueness
  │       → fails here, before any question is asked — FR-013)
  │
  ├─ 2. build one QaAgentQuestionAnswerer from target_config (one AgentSettings, one
  │      DatasetSelector, one pair of loggers — reused across all questions; this reused
  │      wiring never carries per-question state, only per-run configuration)
  │
  ├─ 3. for each Question in testset.questions (strictly sequential, isolated — research.md §2):
  │        result = answerer.answer(question.question)      [qa_agent.answer_question]
  │        match_status = "errored" if result.errored else matcher.grade(question.expected, result.answer)
  │        append QuestionResult(...)
  │      (a question's own failure never stops the loop — FR-004; qa_agent already never raises)
  │
  ├─ 4. compute RunSummary from all QuestionResults, including the target_unreachable
  │      heuristic (research.md §6)
  │
  └─ 5. RunStore.save(TestRun{...})                   [written exactly once — research.md §7]
        → returns the saved run_id/path

compare_runs(run_a_path, run_b_path)
  │
  ├─ 1. RunStore.load(run_a_path), RunStore.load(run_b_path)   → TestRun | raises RunLoadError
  ├─ 2. run_a.testset.content_hash == run_b.testset.content_hash ?
  │        no  → raise IncompatibleRunsError                    [FR-011, Edge Cases]
  │        yes → continue
  ├─ 3. join QuestionResults by n → one ComparisonEntry each     [research.md §8]
  └─ 4. RunComparison{run_a target, run_b target, entries, summary}
```
