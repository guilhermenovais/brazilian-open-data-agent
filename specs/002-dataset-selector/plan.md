# Implementation Plan: Dataset Selector

**Branch**: `002-dataset-selector` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-dataset-selector/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See
`.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build the plain-Python capability the agent uses to obtain the right dataset for a question:
given a question, return that dataset's briefing text plus a ready-to-use
`data_access.dataset.Dataset` handle onto its data files (FR-001/FR-002), and record the
decision as usage data (FR-007). Only one dataset (`orcamentos-aeb-csv`) is registered today,
so selection is trivial — but the spec explicitly names its future replacement ("thousands of
datasets... subagents and RAG") and its future storage model ("datasets downloaded on
demand"), so the selection strategy and the dataset-location strategy are each defined behind
a small `Protocol` now, per Constitution Engineering Principle 2, with today's single
always-the-same-answer implementation behind each. The result type reuses the existing
`Dataset` abstraction from `001-data-access-tools` as-is for "location of the dataset's data
files" (research.md §6), rather than inventing a parallel location type.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `pydantic` v2 (I/O models, Engineering Principle 5); the existing
`data_access` package (`Dataset`, reused directly — research.md §6); Python stdlib
`pathlib`/`json`/`datetime` for briefing/location/log I/O

**Storage**: N/A for reads (no database) — briefings are `.md` files under `data/briefings/`,
dataset folders under `data/datasets/`, both read-only. Usage log is a local append-only JSONL
file (default path `data/logs/dataset_selections.jsonl`, research.md §9) — the only write path
this feature has.

**Testing**: pytest — contract tests mirroring spec.md's Acceptance Scenarios 1:1, plus unit
tests for `LocalDatasetLocator`, `FileBriefingSource`, and `JsonlSelectionLogger` in isolation

**Target Platform**: Linux server process — library consumed in-process by the agent codebase
(same as `001-data-access-tools`; no network service of its own)

**Project Type**: single project (Python library) — `src/` layout, Option 1 from the template

**Performance Goals**: Not specified by the spec; selection over one dataset is O(1) today

**Constraints**: Read-only against `data/briefings/` and `data/datasets/`; the only write is
appending one JSONL line per selection call (FR-007)

**Scale/Scope**: 1 public capability (`select_dataset`) over 1 registered dataset today; the
spec explicitly scopes multi-dataset selection logic out (Assumptions)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| I. Reproducibility Over One-Off Results | N/A directly — no accuracy/comparison claim. Correctness enforced by contract tests traceable 1:1 to Acceptance Scenarios. **Pass.** |
| II. Evidence Before Implementation | Every abstraction here (DatasetSelector, DatasetLocator, BriefingSource Protocols) is justified by text already in spec.md's Input/Assumptions, not speculation — recorded in research.md §2/§4/§5. **Pass.** |
| III. Documentation Is a Deliverable | This plan produces research.md/data-model.md/contracts/quickstart.md; implementation will need docstrings on the non-obvious "never hardcode the key" design (research.md §3). **Pass**, carried into tasks. |
| IV. Tests Document Behavior | Contract tests named after Acceptance Scenarios (research.md §10/quickstart.md). **Pass.** |
| V. Separate Mechanism from Domain Knowledge | `StaticDatasetSelector` contains no dataset-specific facts — `"orcamentos-aeb-csv"` exists only as a filename in `data/briefings/`, never as code (research.md §3). **Pass**, strongly aligned — this is the feature's central design decision. |
| VI. Deterministic Computation Over Model Judgment | Selection is pure deterministic code; today's implementation doesn't even need to interpret the question (spec Edge Case). No model call anywhere in this feature. **Pass.** |
| VII. Code Quality Is Enforced | Each `Protocol` introduced is justified by an explicit, cited piece of spec text (research.md §2/§4/§5) — not a speculative abstraction. No settings/config-object layer added since none exists elsewhere in the codebase yet (research.md, Eng. Principle 7 row below). **Pass.** |
| VIII. Security and Data Stewardship | Read-only against local files; the one write path (usage log) contains no credentials. **Pass** (largely N/A). |
| IX. Continuous Integration Gate | pytest + pyright wired into CI is part of this feature's definition of done; tracked as a task in tasks.md. **Pass**, pending task generation. |
| X. Usage as Research Data | Directly in scope via FR-007/SC-005 — this is the first feature where this principle is an explicit functional requirement, not deferred. `SelectionLogger`/`JsonlSelectionLogger` (research.md §7) implement it. **Pass.** |
| Eng. Principle 1 (thin wiring layer) | No `pydantic-ai` import anywhere in this feature (research.md §1), same scope boundary as `001-data-access-tools`. **Pass.** |
| Eng. Principle 2 (interface before 2nd impl) | `DatasetSelector`, `DatasetLocator`, `BriefingSource`, `SelectionLogger` Protocols each defined now, each justified by spec text naming its future second implementation (research.md §2/§4/§5/§7). **Pass.** |
| Eng. Principle 3 (polymorphic format dispatch) | N/A — no file-format dispatch concern in this feature. |
| Eng. Principle 4 (DI over globals) | `selector`/`logger` are explicit parameters to `select_dataset`; `LocalDatasetLocator`/`FileBriefingSource`/`JsonlSelectionLogger` all take their root paths via constructor, no module-level globals. **Pass.** |
| Eng. Principle 5 (validated pydantic boundary) | `DatasetSelectionResult`/`DatasetSelectionLogEntry` are pydantic models; errors are typed exceptions (data-model.md). One documented adjustment: `DatasetSelectionResult` needs `arbitrary_types_allowed=True` to embed the existing (non-pydantic) `Dataset` class (research.md §6). **Pass**, with a recorded, justified adjustment. |
| Eng. Principle 6 (tool functions testable without a model) | `select_dataset` and every `Protocol` implementation are plain functions/classes; no model needed to test any of them. **Pass.** |
| Eng. Principle 7 (typed centralized settings) | Not introduced in this feature — no `pydantic-settings` object exists anywhere yet in this codebase, and adding one only for this feature's two file paths would be premature (Constitution VII). Paths are explicit constructor arguments instead, same pattern as `Dataset(root_path=...)`. **N/A, deliberately deferred.** |
| Eng. Principle 8 (prompts/briefings versioned) | Briefings are already named, diffable `.md` files under `data/briefings/`; this feature reads them as-is, adding no new versioning machinery. **Pass** (nothing new required). |
| Eng. Principle 9 (native instrumentation preferred) | Documented, deliberate gap: `JsonlSelectionLogger` is a minimal bespoke logger, not native tracing, because no pydantic-ai/tracing wiring exists yet anywhere in this codebase (Eng. Principle 1's scope boundary). Built as a swappable `Protocol` implementation specifically so it can be replaced once that wiring exists (research.md §7). **Documented exception, not a violation** — no simpler alternative satisfies FR-007 today. |
| Eng. Principle 10 (static typing enforced) | pyright in CI (research.md §10), tracked as a task. **Pass**, pending task generation. |

No violations requiring justification beyond the two documented, deliberate exceptions above
(Eng. Principle 7 deferred; Eng. Principle 9's gap explicitly noted as temporary). Complexity
Tracking table left empty.

## Project Structure

### Documentation (this feature)

```text
specs/002-dataset-selector/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── selection.md
│   └── errors.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── dataset_selector/
    ├── __init__.py
    ├── models.py          # DatasetSelectionResult, DatasetSelectionLogEntry
    ├── exceptions.py       # DatasetSelectorError, DatasetNotFoundError,
    │                       # BriefingNotFoundError, NoBriefingsAvailableError
    ├── briefing.py          # BriefingSource Protocol + FileBriefingSource
    ├── locator.py            # DatasetLocator Protocol + LocalDatasetLocator
    ├── selector.py             # DatasetSelector Protocol + StaticDatasetSelector
    ├── usage_log.py             # SelectionLogger Protocol + JsonlSelectionLogger
    └── capabilities.py           # select_dataset — the one public entry point

tests/
├── contract/
│   └── dataset_selector/
│       └── test_selection.py     # 1:1 with US1/US2 Acceptance Scenarios
├── unit/
│   └── dataset_selector/
│       ├── test_locator.py        # key→folder resolution, DatasetNotFoundError (FR-005)
│       ├── test_briefing.py        # list_keys()/get(), BriefingNotFoundError
│       └── test_usage_log.py        # JSONL append, one line per call (FR-007)
└── fixtures/
    └── dataset_selector/
        ├── briefings/
        │   └── sample-key.md
        └── datasets/
            └── sample-key/
                └── data.csv
```

**Structure Decision**: Single-project library layout, same as `001-data-access-tools`
(`src/<package>/`, `tests/{contract,unit}/<package>/`, `tests/fixtures/<package>/`) — this
feature adds a sibling package, `dataset_selector`, consumed in-process alongside
`data_access` (which it reuses directly for its result type, research.md §6). No CLI/web
surface.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations recorded — table intentionally left empty. (Two deliberate, documented
exceptions are recorded in the Constitution Check table above — Eng. Principles 7 and 9 —
neither is a violation requiring a simpler-alternative-rejected justification here, since each
row already states why no simpler alternative satisfies this feature's requirements today.)
