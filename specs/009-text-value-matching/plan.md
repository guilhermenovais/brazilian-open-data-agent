# Implementation Plan: Forgiving Text Matching and Value Suggestions

**Branch**: `009-text-value-matching` | **Date**: 2026-09-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-text-value-matching/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

In the 008 evidence run, text filters with the wrong spelling returned 0 rows and the agent
declined, even though the data held the answer. This feature changes the three data access
tools so the agent can reach stored text. There is no prompt change.

1. **Forgiving matching (US1)**: a new plain-Python module, `data_access/text_matching.py`,
   normalizes both sides (NFKD, no accents, casefold, punctuation as spaces). `equals`
   compares whole normalized values. `contains` requires every non-stopword query word to
   start a stored word, in any order. `PandasQueryEngine` receives these rules at
   construction, so `query_rows` and `aggregate_rows` change together.
2. **Suggestions (US2)**: when a result is empty, the capability checks each text condition
   alone against the unfiltered source. For each condition that matches nothing, it ranks
   the field's distinct stored values by word-start overlap, counting the value's acronym
   as an extra token. It then attaches up to 5 `value_suggestions`. Non-empty results
   serialize exactly as before.
3. **Value lists (US3)**: for each field, `inspect_schema` adds `distinct_count` over the
   whole source, plus the full raw `values` list when there are at most 30.
4. **Config and evidence**: a typed `TextMatchingConfig` (threshold 30, max 5 suggestions,
   stopwords `pt_v1` from a versioned text file) goes from `AgentSettings` through
   `AgentDeps` to the tools, and is recorded on `TestRun`/`ConversationRun`. The tool
   descriptions state the new behavior. The feature is evaluated with one conversation run
   and one standalone run against the 008 baselines, analyzed by a feature-local script.

A planning prototype on `dados_gerais/tb_geral.csv` confirms SC-002 at the mechanism level.
"AEB" ranks "Agência Espacial Brasileira" first, and the Amazônia-1 failure was a case-only
mismatch that normalization alone fixes (research.md).

## Technical Context

**Language/Version**: Python 3.11+ (venv 3.12)

**Primary Dependencies**: `pandas` 3.0 (masks via a per-distinct-value `map`), `pydantic`
2.13 (`Field(exclude_if=…)` keeps empty-suggestion results byte-identical), `pydantic-ai`
(tool docstrings → tool descriptions), `pydantic-settings`, and the standard library
`unicodedata`/`re`. No new dependency.

**Storage**: New versioned artifact `src/data_access/stopwords/pt_v1.txt` (package data).
Run files in `data/testset_runs/` and `data/conversation_runs/` gain an optional
`text_matching` object. Results go to `specs/009-text-value-matching/results.md`.

**Testing**: pytest + pyright (existing CI). Unit tests cover the pure matching and ranking
functions. Contract tests on a new fixture CSV with accented, hyphenated and punctuated
Portuguese names cover US1–US3 through the public capabilities. The existing data access
tests must pass unedited (SC-006). `FunctionModel`-captured tool definitions check
FR-018.

**Target Platform**: Linux, local processes (`testset_runner.cli`, `web_ui.cli`).

**Project Type**: Single-project Python library + CLIs (`src/` layout).

**Performance Goals**: Non-empty queries do the same work as today, plus one normalization
per distinct value per text condition. Empty results add one engine pass per text condition
and one ranking pass over the field's distinct values. Both are negligible on the evaluated
source (≤ 438 rows) and linear in the number of distinct values in general (research.md R4).

**Constraints**: Stored values are never altered in any output (FR-006). Range filters,
errors and result caps are unchanged (FR-007). `system_v1.md`/`system_v2.md` are unchanged
(FR-018). `data_access` stays free of `pydantic_ai` and of `qa_agent` imports (Eng. 1).
The value lists have no size cap (Clarifications Q4).

**Scale/Scope**: New `data_access/text_matching.py`, `data_access/stopwords/pt_v1.txt` and
`specs/009-text-value-matching/analyze_runs.py`. Edits to `data_access/{models,
query_engine,capabilities}.py`, `qa_agent/{tools,settings,deps,capabilities,answerer}.py`
and `testset_runner/{models,conversation_models,runner,conversation_runner,cli}.py`. One
new test fixture and about 4 new or extended test modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| I. Reproducibility | Before and after are both recorded runs under the same target and settings. The runs carry `text_matching`. `compare` and `analyze_runs.py` derive every number in results.md from run files (research.md R8). **Pass.** |
| II. Evidence Before Implementation | Motivated by 008 run `20260925T095751382002Z`, cause 1 (spec Evidence). The planning prototype reproduced the failing values against the real source. The effect is measured, not assumed (FR-019). **Pass.** |
| III. Documentation Is a Deliverable | research.md records every decision with its rejected alternatives. The contracts give traceability tables. The docstrings of `text_matching.py`, the engine and the capabilities are updated. results.md is a task. **Pass**, carried into tasks. |
| IV. Tests Document Behavior | Contract tests are named after US/FR scenarios, and the contract tables map one-to-one to test cases. The behavior change for missing values is stated by a dedicated test. **Pass.** |
| V. Separate Mechanism from Domain Knowledge | Matching and ranking contain no dataset fact. Stopwords are a named language artifact, not code (FR-004). AEB and CBERS appear only in fixtures, contracts and results. The value-list threshold is configuration. **Pass.** |
| VI. Deterministic Over Model Judgment | Normalization, matching, the per-condition zero check, ranking and tie-breaks are all deterministic. The model only chooses whether to retry with a suggested value. **Pass.** |
| VII. Code Quality / Simplicity | Standard library only. One config object with three fields and no new CLI flag or env var. No cap or tool without a demonstrated need. The conversation comparison stays a feature-local script instead of a new runner subcommand. **Pass.** |
| VIII. Security & Data Stewardship | No credentials involved. The run records gain only non-secret numbers and a list name. **Pass.** |
| IX. CI Gate | All new tests run in the existing `pytest` + `pyright` CI. The live evaluation is outside CI, as in 004–008. **Pass.** |
| X. Usage as Research Data | Suggestions and value lists are part of tool results, so they are captured in each step's `result_summary` in run files and traces with no extra logging. The zero-row audit in `analyze_runs.py` reads them from there. **Pass.** |
| Eng. 1 (thin wiring) | All logic is in `data_access` (no `pydantic_ai`). The tool wrappers only forward `ctx.deps.text_matching`. **Pass.** |
| Eng. 2 (interface before 2nd impl) | The `QueryEngine` protocol's method signatures are unchanged. The matching rules are a constructor argument of `PandasQueryEngine`, so a future DuckDB engine receives the same `MatchRules`. No new protocol is needed (one implementation). **Pass.** |
| Eng. 3 (polymorphic dispatch) | N/A. The condition-type dispatch in `_condition_mask` is the existing pattern and is not extended with new types. |
| Eng. 4 (DI over globals) | The module-level `_ENGINE` is replaced by an engine built per call from the injected `TextMatchingConfig`. The config flows through `AgentDeps`. **Pass.** |
| Eng. 5 (validated boundary) | `ValueSuggestion`, `SuggestedValue`, the extended `FieldInfo`/results and `TextMatchingConfig` are pydantic models with constraints. **Pass.** |
| Eng. 6 (testable without a model) | Every behavior is tested through plain capability or pure functions. Only the description check uses a `FunctionModel`. **Pass.** |
| Eng. 7 (typed centralized settings) | `AgentSettings.text_matching: TextMatchingConfig`, recorded per run (FR-016). **Pass.** |
| Eng. 8 (versioned prompts/tool schemas) | Prompts are not touched. Stopwords are versioned by file name. The tool description change is marked by the presence of `text_matching` in run records, the same approach 007 used for its description change (research.md R6/R7). **Pass.** |
| Eng. 9 (native instrumentation) | Unchanged. **Pass.** |
| Eng. 10 (static typing) | Full hints, with pyright in CI. **Pass.** |

**Post-design re-check (after Phase 1)**: still **Pass** on all rows. Phase 1 added two
result models, three optional fields on existing results, one config model and one data
file. No dependency, protocol change or prompt version was added. The only intentional
behavior change beyond the spec's stories is that missing values never match text filters.
The spec's Edge Cases require it, it is documented in contracts/text-matching.md, and a test
covers it.

## Project Structure

### Documentation (this feature)

```text
specs/009-text-value-matching/
├── plan.md                          # This file
├── research.md                      # Phase 0
├── data-model.md                    # Phase 1
├── quickstart.md                    # Phase 1
├── contracts/
│   ├── text-matching.md             # equals/contains normalization rules (US1)
│   ├── value-suggestions.md         # empty-result suggestions + ranking (US2)
│   ├── schema-inspection.md         # distinct_count / values (US3)
│   └── agent-tools-and-runs.md      # tool descriptions, settings, run records, CLI line
├── checklists/requirements.md       # from /speckit-specify
├── analyze_runs.py                  # implementation phase: before/after analysis (R8)
├── results.md                       # implementation phase: live evaluation record
└── tasks.md                         # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
src/
├── data_access/
│   ├── text_matching.py        # NEW: TextMatchingConfig, MatchRules, normalize/words/acronym,
│   │                           #      equals/contains/overlap, rank_candidates, load_stopwords
│   ├── stopwords/pt_v1.txt     # NEW: versioned Portuguese stopword list
│   ├── models.py               # + SuggestedValue, ValueSuggestion; FieldInfo.distinct_count/values;
│   │                           #   SchemaInspectionResult.value_list_threshold; value_suggestions on
│   │                           #   RowQueryResult/AggregationResult; Equals/Contains value descriptions
│   ├── query_engine.py         # PandasQueryEngine(rules); equals/contains via MatchRules; missing never matches
│   └── capabilities.py         # text_matching kwarg; per-call engine; suggestions on empty results; value lists
├── qa_agent/
│   ├── tools.py                # forward ctx.deps.text_matching; docstrings for inspect_schema/query_rows/aggregate_rows
│   ├── settings.py             # + text_matching
│   ├── deps.py                 # + text_matching (default factory)
│   ├── capabilities.py         # AgentDeps(..., text_matching=settings.text_matching)
│   └── answerer.py             # + text_matching param/property
└── testset_runner/
    ├── models.py               # + TestRun.text_matching
    ├── conversation_models.py  # + ConversationRun.text_matching
    ├── runner.py               # run_testset(..., text_matching=None)
    ├── conversation_runner.py  # run_conversations(..., text_matching=None)
    └── cli.py                  # pass answerer.text_matching; "Text matching: …" report line

pyproject.toml                  # package data: data_access/stopwords/*.txt

tests/
├── fixtures/data_access/sample_dataset/budget_actions.csv   # NEW: accented/hyphenated PT names
├── unit/data_access/test_text_matching.py                   # NEW: pure rules + ranking
├── contract/data_access/test_text_matching_filters.py       # NEW: US1 via query_rows/aggregate_rows
├── contract/data_access/test_value_suggestions.py           # NEW: US2
├── contract/data_access/test_inspection.py                  # + US3 cases
├── unit/qa_agent/test_tools_description.py                  # + FR-018 facts
├── contract/testset_runner/test_run_testset.py              # + text_matching recorded
└── contract/testset_runner/test_run_conversations.py        # + text_matching recorded
```

**Structure Decision**: Keep the single `src/` layout. All matching logic goes in
`data_access`, the package that owns filtering. `qa_agent` and `testset_runner` only carry
and record the config. The new fixture sits in the existing `sample_dataset`. The
discovery tests check membership only, not a source count, so adding it is safe.

## Complexity Tracking

No Constitution Check violations. The table is intentionally empty.
