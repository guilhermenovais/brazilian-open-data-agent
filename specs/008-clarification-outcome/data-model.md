# Data Model: Clarification Outcome, Prompt v2 and Outcome-Based Grading

**Feature**: `008-clarification-outcome` | **Date**: 2026-09-24

This feature changes existing pydantic models only, except for one new exception type.
Every change is additive or widens a type, so stored run files and JSONL logs load unchanged
(FR-003, SC-006). The "research" references point to [research.md](./research.md).

## Shared type

### `Outcome` (new alias, `qa_agent/models.py`)

```text
Outcome = Literal["full", "partial", "none", "needs_clarification"]
```

| Value | Meaning (the agent's own classification) |
|---|---|
| `full` | The question was answered in full from queried data. |
| `partial` | Part of the question was answered, and the rest is declared as not covered. |
| `none` | Nothing could be answered: not covered, no match, or a processing failure. |
| `needs_clarification` | **New.** The question has several readings with different amounts. The answer is a clarifying question with no dataset values. |

Used by every field listed below instead of a written-out literal (research §1).

## `qa_agent` models

| Model | Field | Before | After |
|---|---|---|---|
| `AgentAnswer` | `outcome` | `Literal[full, partial, none]` | `Outcome` |
| `QuestionAnsweringResult` | `outcome` | `Literal[full, partial, none]` | `Outcome` |
| `QuestionAnsweringResult` | `briefing_fingerprint` | — | **new** `str \| None = None`: SHA-256 hex of the briefing text used. `None` when dataset selection failed (research §5). |
| `AgentRunLogEntry` | `outcome` | `Literal[full, partial, none]` | `Outcome` |

`AgentRunLogEntry` gains no prompt-version field. Recording the version in the usage log is
out of scope (spec Assumptions).

### `AgentSettings` (`qa_agent/settings.py`)

| Field | Type | Default | Env | Validation |
|---|---|---|---|---|
| `prompt_version` | `str` | `DEFAULT_PROMPT_VERSION` (`"v2"`) | `QA_AGENT_PROMPT_VERSION` | Must be in `prompt_loader.available_versions()`. Otherwise it fails with a message naming the version and listing the available ones (FR-009). |

### `UnknownPromptVersionError` (new, `qa_agent/exceptions.py`)

A subclass of `ValueError`, so a pydantic `field_validator` can raise it. It has the
attributes `requested: str` and `available: list[str]`. `str(exc)` is
`"unknown prompt version 'v9' (available: v1, v2)"`.

### Outcome clamp (behavior, `qa_agent/capabilities.py`)

The table shows the final outcome for each combination of reported outcome and
`budget.successes`:

| Reported outcome | `successes == 0` | `successes ≥ 1` |
|---|---|---|
| `full` | `none` | `full` |
| `partial` | `none` | `partial` |
| `none` | `none` | `none` |
| `needs_clarification` | **`needs_clarification`** (FR-004) | `needs_clarification` |

Errored paths (selection failure, agent exception) keep producing `outcome="none"`.

## `testset_runner` models

### `Question` (a testset record)

| Field | Type | Notes |
|---|---|---|
| `expected_outcome` | `Outcome \| None = None` | **New**, optional. A value outside `Outcome` makes the whole testset fail to load with `TestsetLoadError` (FR-012). |

In the bundled testset this is set on #48 = `none`, #49 = `needs_clarification` and
#50 = `none` (FR-019). The file's `content_hash` changes as a result (research §7).

### `QuestionResult`

| Field | Before | After |
|---|---|---|
| `agent_outcome` | `Literal[full, partial, none]` | `Outcome` |
| `expected_outcome` | — | **new** `Outcome \| None = None`: the value the result was graded against. `None` means the record had none, or it is a run from before this feature (FR-018). |

### `TargetConfiguration`

| Field | Type | Notes |
|---|---|---|
| `prompt_version` | `str \| None = None` | **New.** Set by the runner CLI from `answerer.prompt_version`. `None` means not recorded (runs from before this feature) (research §4). |

### `TestRun`

| Field | Type | Notes |
|---|---|---|
| `briefing_fingerprints` | `list[str] \| None = None` | **New.** Sorted, distinct, non-`None` `briefing_fingerprint`s of all results. Normally one element. `[]` if every question failed dataset selection. `None` means not recorded (research §5). |

### `RunComparison`

| Field | Type | Notes |
|---|---|---|
| `briefing_fingerprints_a` / `_b` | `list[str] \| None = None` | **New.** Copied from each run. Shown for information only. |
| `briefing_fingerprints_differ` | `bool` | **New.** `briefing_fingerprints_a != briefing_fingerprints_b`. When both are `None` they are equal, so this is `False`. Doesn't affect transitions (FR-011). |

The prompt versions are shown through the existing `run_a` / `run_b`
(`TargetConfiguration`) fields.

## Grading state table (FR-013–FR-017)

Input: the testset record (`expected`, `expected_outcome`) and the agent result (`errored`,
`outcome`, `answer`).

| # | Condition (checked in order) | `match_status` |
|---|---|---|
| 1 | `errored` | `errored` (decided in the runner, before grading) |
| 2 | `expected_outcome is None` | `NumericMatchStrategy.evaluate(expected, answer)`, as today |
| 3 | `outcome != expected_outcome` | `not_matched` |
| 4 | `expected_outcome ∈ {none, needs_clarification}` and `contains_amount(answer)` | `not_matched` |
| 5 | `expected_outcome ∈ {none, needs_clarification}` | `matched` |
| 6 | `expected_outcome ∈ {full, partial}` | `NumericMatchStrategy.evaluate(expected, answer)` (matched / not_matched / needs_review) |

`contains_amount(text)` is true when any of these patterns match: `R\$\s*-?\d`, `\d[.,]\d`
or `\d\s*%` (research §6).

## Artifacts (versioned files)

| Artifact | Change |
|---|---|
| `src/qa_agent/prompts/system_v1.md` | **Unchanged**, byte for byte (FR-005). A test pins its SHA-256. |
| `src/qa_agent/prompts/system_v2.md` | **New** ([contracts/prompt-v2.md](./contracts/prompt-v2.md)). |
| `data/briefings/orcamentos-aeb-csv.md` | Edited in place: new "Qual medida a pergunta pede" section (research §8). Identified on each run by its fingerprint. |
| `data/testsets/orcamentos-aeb-csv.json` | Three records gain `expected_outcome`. |
