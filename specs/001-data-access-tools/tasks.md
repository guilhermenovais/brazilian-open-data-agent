---

description: "Task list for Data Access Tool Layer implementation"
---

# Tasks: Data Access Tool Layer

**Input**: Design documents from `/specs/001-data-access-tools/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included. plan.md's Testing field and Project Structure explicitly specify pytest
contract tests mirroring spec.md's Acceptance Scenarios 1:1 plus targeted unit tests
(research.md §11); Constitution Principles IV and IX make this a hard requirement, not an
optional add-on.

**Organization**: Tasks are grouped by user story (spec.md priorities P1–P4) to enable
independent implementation and testing of each capability.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unmet dependency)
- **[Story]**: Which user story this task belongs to (US1–US4)
- File paths are exact, per plan.md's Project Structure

## Path Conventions

Single-project Python library layout (plan.md): `src/data_access/`, `tests/` at repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project directory structure: `src/data_access/`, `src/data_access/readers/`, `tests/contract/`, `tests/unit/`, `tests/fixtures/` per plan.md Project Structure
- [X] T002 Initialize `pyproject.toml` for Python 3.11+ with `pydantic` v2, `pandas`, `pytest`, `pyright` as dependencies, configured for editable install (`pip install -e ".[dev]"` per quickstart.md Setup)
- [X] T003 [P] Configure `pyright` strict-mode settings (`[tool.pyright]` in `pyproject.toml` or `pyrightconfig.json`) per research.md §10
- [X] T004 [P] Create `tests/fixtures/sample_dataset/` per quickstart.md Prerequisites: `customers.csv` (US-style numbers), `orders/2024/sales.csv` (nested subfolder; `amount` column mixes Brazilian-style `"1.234,56"` and US-style `"1,234.56"` values row-to-row within the same column, per US4 Acceptance Scenario 6 / FR-010), `products.json` (array of flat, heterogeneous objects), `broken.csv` (deliberately malformed, unclosed quote), `README.md` (non-data file)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 [P] Create `src/data_access/exceptions.py`: `DataAccessError` base class + `DataSourceNotFoundError`, `UnreadableSourceError`, `FieldNotFoundError`, `NumericTypeError`, `IdentifierCollisionError` per contracts/errors.md
- [X] T006 [P] Create `src/data_access/readers/base.py`: `DataSourceReader` Protocol (`read(path: Path) -> pandas.DataFrame`) per data-model.md
- [X] T007 [P] Create `src/data_access/readers/csv_reader.py`: `CsvReader` reading all columns as strings (`dtype=str`), raising a parse error on malformed input, per research.md §2 (depends on T006)
- [X] T008 [P] Create `src/data_access/readers/json_reader.py`: `JsonReader` for a top-level array of flat objects, taking the key-union across records and coercing scalar leaves to strings, per research.md §2, §8 (depends on T006)
- [X] T009 Create `src/data_access/readers/__init__.py` exporting `DataSourceReader`, `CsvReader`, `JsonReader` (depends on T006, T007, T008)
- [X] T010 Create `src/data_access/dataset.py`: `Dataset` abstraction — recursive folder walk (including subfolders) building an internal tree/index, POSIX relative-path identifier derivation, `IdentifierCollisionError` detection, extension-based (`.csv`/`.json`) non-data-file filtering, `list_sources() -> list[DataSourceInfo]`, `resolve(identifier) -> Path` per data-model.md (depends on T005, T009)
- [X] T011 [P] Unit tests for `Dataset` identifier derivation, collision detection, and non-data-file filtering in `tests/unit/test_dataset.py` per research.md §11 (depends on T010). Collision detection MUST NOT rely on the host filesystem's case sensitivity (CI runs on case-sensitive Linux): build a dedicated, test-local temp directory (`tmp_path`) containing two physical files whose derived relative-path identifiers collide (e.g. same name differing only in case, such as `data.csv` and `DATA.csv`, both real files on the case-sensitive test FS) and assert `IdentifierCollisionError` naming both physical paths — do not add this fixture to the shared `tests/fixtures/sample_dataset/`
- [X] T012 Create `src/data_access/__init__.py` package exports

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Discover Available Data (Priority: P1) 🎯 MVP

**Goal**: List every queryable data source in a dataset with a stable identifier and format, excluding non-data files, flagging unreadable sources, without erroring on empty datasets.

**Independent Test**: Point the tool layer at a dataset containing a mix of CSV and JSON files and confirm `discover_data_sources` alone returns an accurate, complete list — with no dependency on any other capability.

### Tests for User Story 1

- [X] T013 [P] [US1] Contract tests for discovery in `tests/contract/test_discovery.py`, one test per Acceptance Scenario US1.1–US1.5 plus the FR-012a identifier-collision case, per contracts/discovery.md. Like T011, the collision case MUST use its own dedicated test-local temp directory (two files whose identifiers collide, e.g. differing only by case) rather than `tests/fixtures/sample_dataset/`, so it stays deterministic across filesystems

### Implementation for User Story 1

- [X] T014 [US1] Create `src/data_access/models.py` with `DataSourceInfo` and `DiscoveryResult` pydantic models per data-model.md
- [X] T015 [US1] Implement `discover_data_sources(dataset: Dataset) -> DiscoveryResult` in `src/data_access/capabilities.py` per contracts/discovery.md (depends on T014, T010)

**Checkpoint**: User Story 1 is fully functional and testable independently — MVP deliverable.

---

## Phase 4: User Story 2 - Inspect Schema & Sample Before Querying (Priority: P2)

**Goal**: Given a data source identifier, return its field names and a bounded, unmodified sample of real records, with numeric-like fields flagged.

**Independent Test**: Given a known data source identifier, request its schema and confirm the response includes field names and a bounded sample of real records — including locale-formatted numbers shown as found — without needing query or aggregation.

### Tests for User Story 2

- [X] T016 [P] [US2] Contract tests for schema inspection in `tests/contract/test_inspection.py`, US2.1–US2.5, per contracts/inspection.md
- [X] T017 [P] [US2] Unit tests for `parse_locale_number()` edge cases (pure integers, `,`+`.` mixed, single-separator ambiguous cases, unparseable strings) in `tests/unit/test_numeric.py` per research.md §3

### Implementation for User Story 2

- [X] T018 [US2] Implement `src/data_access/numeric.py`: `parse_locale_number(raw: str) -> float | None` per research.md §3, plus the ≥80%-of-sample `numeric_like` classification rule per research.md §4
- [X] T019 [US2] Add `FieldInfo` and `SchemaInspectionResult` models to `src/data_access/models.py` per data-model.md (depends on T014)
- [X] T020 [US2] Implement `inspect_schema(dataset: Dataset, identifier: str) -> SchemaInspectionResult` in `src/data_access/capabilities.py` with `SAMPLE_SIZE_CAP = 20`, raw (never re-formatted) sample values, per contracts/inspection.md (depends on T018, T019)

**Checkpoint**: User Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 - Query Rows Matching Specific Conditions (Priority: P3)

**Goal**: Retrieve rows matching one or more AND-combined filter conditions (equality, contains, numeric range), with numeric ranges evaluated on true normalized values.

**Independent Test**: Using a data source and field identified via discovery/inspection, submit a filter (including a numeric range on a locale-formatted field) and confirm returned rows match — and only match — the stated condition.

### Tests for User Story 3

- [X] T021 [P] [US3] Contract tests for filtered row query in `tests/contract/test_query.py`, US3.1–US3.9 (the last three covering `DataSourceNotFoundError`, `UnreadableSourceError`, and `NumericTypeError` on a non-numeric-like range target, per contracts/query.md's Errors table), per contracts/query.md

### Implementation for User Story 3

- [X] T022 [US3] Add `EqualsCondition`, `ContainsCondition`, `RangeCondition` (discriminated union) and `RowQueryResult` models to `src/data_access/models.py` per data-model.md (depends on T019)
- [X] T023 [US3] Implement `src/data_access/query_engine.py`: `QueryEngine` Protocol + `PandasQueryEngine.query_rows()` (equality/contains/range filtering, AND-combined, using `numeric.py` for range comparisons) per research.md §6
- [X] T024 [US3] Implement `query_rows(dataset, identifier, filters) -> RowQueryResult` in `src/data_access/capabilities.py` with `ROW_QUERY_CAP = 100` and `truncated`/`total_match_count` semantics per contracts/query.md (depends on T022, T023)

**Checkpoint**: User Stories 1, 2, AND 3 all work independently.

---

## Phase 6: User Story 4 - Aggregate Rows Into Grouped Summaries (Priority: P4)

**Goal**: Group rows by one or more fields and compute count/sum aggregates over a value field, with numerically correct sums regardless of locale formatting.

**Independent Test**: Using a known data source, group by one categorical field and compute a count and a sum over a locale-formatted numeric field, and confirm grouped totals are numerically correct.

### Tests for User Story 4

- [X] T025 [P] [US4] Contract tests for aggregation in `tests/contract/test_aggregation.py`, US4.1–US4.8 (the last two covering `DataSourceNotFoundError` and `UnreadableSourceError`, per contracts/aggregation.md's Errors table), per contracts/aggregation.md

### Implementation for User Story 4

- [X] T026 [US4] Add `AggregateSpec`, `AggregationRequest`, `AggregationGroup`, `AggregationResult` models to `src/data_access/models.py` per data-model.md (depends on T022)
- [X] T027 [US4] Implement `PandasQueryEngine.aggregate()` in `src/data_access/query_engine.py` (multi-field `group_by`, `count`/`sum`, per-value locale normalization via `numeric.py`) per research.md §6, data-model.md (depends on T023)
- [X] T028 [US4] Implement `aggregate_rows(dataset, identifier, request) -> AggregationResult` in `src/data_access/capabilities.py` per contracts/aggregation.md (depends on T026, T027)

**Checkpoint**: All four user stories are independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, CI, and end-to-end validation across all stories

- [X] T029 [P] Add module-level docstrings documenting the non-obvious parsing heuristic in `src/data_access/numeric.py` and the `Dataset` abstraction's folder/identifier model in `src/data_access/dataset.py`, per Constitution Principle III and plan.md
- [X] T030 Wire `pytest` (`tests/contract`, `tests/unit`) and `pyright` (`src/`) into CI (e.g. `.github/workflows/ci.yml`) per Constitution Principle IX and Engineering Principle 10
- [X] T031 Run the full quickstart.md validation end-to-end (all 5 scenarios) and confirm `pytest tests/contract tests/unit -v` and `pyright src/` both pass clean

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational; reuses `models.py` from US1 (T014) but adds independently — no functional dependency on US1's capability
- **User Story 3 (Phase 5)**: Depends on Foundational; reuses `models.py` from US2 (T019) but adds independently — no functional dependency on US2's capability
- **User Story 4 (Phase 6)**: Depends on Foundational; reuses `models.py`/`query_engine.py` from US3 (T022, T023) but adds independently — no functional dependency on US3's capability
- **Polish (Phase 7)**: Depends on all four user stories being complete

### Within Each User Story

- Tests written first, expected to fail before implementation exists
- Models before capability implementation
- `numeric.py` (US2) before any numeric-dependent logic in US3/US4
- `query_engine.py`'s `query_rows()` (US3) before `aggregate()` is added to the same file (US4)

### Parallel Opportunities

- T003, T004 (Setup) in parallel
- T005, T006 (Foundational) in parallel (no shared dependency); T007, T008 in parallel once T006 lands
- T011 in parallel with subsequent phases' test-writing tasks once T010 lands
- T013 (US1 tests) can be written in parallel with Foundational Phase 2 tasks that don't touch `capabilities.py`/`models.py`
- T016 and T017 (US2 tests) in parallel with each other
- T021 (US3 tests), T025 (US4 tests) can each be drafted as soon as their phase opens, in parallel with that phase's model/engine tasks
- T029 in parallel with T030

---

## Parallel Example: User Story 2

```bash
# Launch both test tasks for User Story 2 together:
Task: "Contract tests for schema inspection in tests/contract/test_inspection.py"
Task: "Unit tests for parse_locale_number() edge cases in tests/unit/test_numeric.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (discovery)
4. **STOP and VALIDATE**: Run `tests/contract/test_discovery.py` independently
5. Demo discovery in isolation if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add User Story 1 (discovery) → validate → MVP
3. Add User Story 2 (schema inspection) → validate
4. Add User Story 3 (filtered row query) → validate
5. Add User Story 4 (aggregation) → validate
6. Phase 7: docs, CI wiring, full quickstart.md run

---

## Notes

- [P] tasks touch different files with no unmet dependency at execution time
- [Story] label maps each task to its user story for traceability back to spec.md
- `models.py` and `query_engine.py` are shared single files touched by multiple stories — later stories' additions to them are sequenced after the earlier story's task, never marked [P] against it
- Every exception type, cap constant, and field name in this file is traceable to a specific FR/contract; no task introduces behavior beyond spec.md's scope
- Commit after each task or logical group; verify contract tests fail before their implementation task lands
