---

description: "Task list template for feature implementation"
---

# Tasks: Dataset Selector

**Input**: Design documents from `/specs/002-dataset-selector/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/selection.md, contracts/errors.md, quickstart.md

**Tests**: Contract tests are explicitly required by this feature (plan.md Testing section: "pytest — contract tests mirroring spec.md's Acceptance Scenarios 1:1, plus unit tests"). Included below.

**Organization**: Tasks are grouped by user story (US1, US2) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

## Path Conventions

Single-project library layout (plan.md Project Structure), matching `001-data-access-tools`:

- `src/dataset_selector/` — implementation package
- `tests/contract/dataset_selector/` — contract tests (1:1 with spec.md Acceptance Scenarios)
- `tests/unit/dataset_selector/` — unit tests for individual `Protocol` implementations
- `tests/fixtures/dataset_selector/` — isolated test fixtures (not the real `data/` tree)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project scaffolding and fixtures shared by every later phase

- [X] T001 Create package skeleton `src/dataset_selector/__init__.py` (empty for now — populated in T005/T010/T016/T021/T026) and test package directories `tests/contract/dataset_selector/__init__.py`, `tests/unit/dataset_selector/__init__.py` per plan.md Project Structure
- [X] T002 [P] Add `data/logs/` to `.gitignore` (research.md §9: usage-log output is generated data, not source — mirrors the existing `*.log` treatment; `.gitignore` currently ignores `*.log` but not `*.jsonl`)
- [X] T003 [P] Create test fixtures `tests/fixtures/dataset_selector/briefings/sample-key.md` (arbitrary briefing text) and `tests/fixtures/dataset_selector/datasets/sample-key/data.csv` (arbitrary CSV content) per quickstart.md Prerequisites, used by isolated unit/contract tests instead of the real `data/` tree

**Checkpoint**: Package and test directories exist; fixtures ready for isolated tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types every user story's implementation and tests depend on — models, exceptions, and the `Protocol` interfaces

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Create `DatasetSelectorError` base exception and `DatasetNotFoundError(key: str)`, `BriefingNotFoundError(key: str)`, `NoBriefingsAvailableError()` in `src/dataset_selector/exceptions.py`, mirroring `data_access.exceptions.DataAccessError`'s pattern (contracts/errors.md; each carries the fields listed in that table)
- [X] T005 [P] Create `DatasetSelectionResult` pydantic v2 model in `src/dataset_selector/models.py` with fields `dataset_key: str` (non-empty; the briefing's file stem, e.g. `"orcamentos-aeb-csv"`), `briefing: str` (the briefing's full raw text content), and `dataset: data_access.dataset.Dataset` (requires `model_config = ConfigDict(arbitrary_types_allowed=True)` per data-model.md, since `Dataset` is not a pydantic model); also create `DatasetSelectionLogEntry` pydantic v2 model in the same file with fields `question: str`, `dataset_key: str`, `timestamp: datetime` (UTC, `datetime.now(timezone.utc)` at capture time)
- [X] T006 [P] Define the `DatasetLocator` Protocol in `src/dataset_selector/locator.py`: `def locate(self, key: str) -> Path: ...` (data-model.md §DatasetLocator)
- [X] T007 [P] Define the `BriefingSource` Protocol in `src/dataset_selector/briefing.py`: `def list_keys(self) -> list[str]: ...` and `def get(self, key: str) -> str: ...` (data-model.md §BriefingSource)
- [X] T008 [P] Define the `SelectionLogger` Protocol in `src/dataset_selector/usage_log.py`: `def log(self, entry: DatasetSelectionLogEntry) -> None: ...` (data-model.md §SelectionLogger; module deliberately not named `logging.py` to avoid shadowing the stdlib module, research.md §7)
- [X] T009 [P] Define the `DatasetSelector` Protocol in `src/dataset_selector/selector.py`: `def select(self, question: str) -> DatasetSelectionResult: ...` (data-model.md §DatasetSelector)

**Checkpoint**: Foundation ready — all Protocols, models, and exceptions exist; user story implementation can now begin

---

## Phase 3: User Story 1 - Obtain the dataset needed to answer a question (Priority: P1) 🎯 MVP

**Goal**: Given any user question, return the `orcamentos-aeb-csv` dataset's briefing text plus a ready-to-use `Dataset` handle onto its data files, and record the decision as a usage-log entry.

**Independent Test**: Submit a dataset selection request with any user question as input and verify the response identifies the `orcamentos-aeb-csv` dataset, includes its briefing, and points to the location of its data files.

### Tests for User Story 1 ⚠️

> Write these tests FIRST, ensure they FAIL before implementation

- [X] T010 [P] [US1] Contract test for Acceptance Scenario 1 in `tests/contract/dataset_selector/test_selection.py`: given a question about federal budget execution for AEB or MCTIC (e.g. `"Quanto foi empenhado pela AEB em 2015?"`), `select_dataset(...)` against the real `data/briefings/` and `data/datasets/` returns a `DatasetSelectionResult` with `dataset_key == "orcamentos-aeb-csv"`, non-empty `briefing` text, and a `dataset` whose folder resolves under `data/datasets/orcamentos-aeb-csv` (contracts/selection.md)
- [X] T011 [P] [US1] Contract test for Acceptance Scenario 2 in `tests/contract/dataset_selector/test_selection.py`: given a question unrelated to any available data (e.g. `"What's the weather like today?"`), `select_dataset(...)` still returns the same `orcamentos-aeb-csv` result as Scenario 1 (FR-003, FR-006 — no "no match" behavior exists in this phase)
- [X] T012 [P] [US1] Contract test for FR-007/SC-005 in `tests/contract/dataset_selector/test_selection.py`: after a successful `select_dataset(...)` call using a `JsonlSelectionLogger` pointed at a temp path, exactly one new JSONL line is appended containing `question`, `dataset_key`, and `timestamp` fields (quickstart.md Scenario 5)
- [X] T013 [P] [US1] Contract test for the `NoBriefingsAvailableError` edge case in `tests/contract/dataset_selector/test_selection.py`: given a `FileBriefingSource` pointed at an empty directory (no `.md` files), `select_dataset(...)` raises `NoBriefingsAvailableError` and no log entry is written (data-model.md Errors table; contracts/selection.md Side effect: "No log entry is written if `selector.select(...)` raises")

### Implementation for User Story 1

- [X] T014 [US1] Implement `FileBriefingSource` in `src/dataset_selector/briefing.py` (after T007's Protocol): constructed with `briefings_root: str | Path`; `list_keys()` returns the sorted `.stem`s of every `*.md` file directly under `briefings_root`; `get(key)` returns `(briefings_root / f"{key}.md").read_text()`, or raises `BriefingNotFoundError(key)` if that file doesn't exist (data-model.md §BriefingSource)
- [X] T015 [US1] Implement `LocalDatasetLocator` in `src/dataset_selector/locator.py` (after T006's Protocol): constructed with `datasets_root: str | Path`; `locate(key)` returns `datasets_root / key` if that folder exists, else raises `DatasetNotFoundError(key)` (data-model.md §DatasetLocator, FR-005)
- [X] T016 [US1] Implement `JsonlSelectionLogger` in `src/dataset_selector/usage_log.py` (after T008's Protocol): constructed with `log_path: str | Path`; `log(entry)` appends `entry.model_dump_json() + "\n"` to that file, creating parent directories on first use (data-model.md §SelectionLogger)
- [X] T017 [US1] Implement `StaticDatasetSelector` in `src/dataset_selector/selector.py` (after T009's Protocol; depends on T014, T015): constructed with `briefing_source: BriefingSource` and `locator: DatasetLocator`; `select(question)` ignores `question`'s content entirely, always selects the lexicographically-first key from `briefing_source.list_keys()` (never a hardcoded dataset name — research.md §3), raises `NoBriefingsAvailableError()` if `list_keys()` returns empty, and otherwise builds `DatasetSelectionResult(dataset_key=key, briefing=briefing_source.get(key), dataset=Dataset(locator.locate(key)))`
- [X] T018 [US1] Implement the public `select_dataset` capability in `src/dataset_selector/capabilities.py` (depends on T005, T008, T009, T017): `def select_dataset(question: str, selector: DatasetSelector, logger: SelectionLogger) -> DatasetSelectionResult` — calls `selector.select(question)`, then on success calls `logger.log(DatasetSelectionLogEntry(question=question, dataset_key=result.dataset_key, timestamp=datetime.now(timezone.utc)))` exactly once, then returns `result`; no log entry is written if `selector.select(...)` raises (contracts/selection.md Side effect)
- [X] T019 [US1] Export public symbols from `src/dataset_selector/__init__.py`: `select_dataset`, `DatasetSelectionResult`, `DatasetSelectionLogEntry`, `DatasetSelector`, `DatasetLocator`, `BriefingSource`, `SelectionLogger`, `StaticDatasetSelector`, `LocalDatasetLocator`, `FileBriefingSource`, `JsonlSelectionLogger`, `DatasetSelectorError`, `DatasetNotFoundError`, `BriefingNotFoundError`, `NoBriefingsAvailableError` (mirrors `data_access/__init__.py`'s pattern)
- [X] T020 [US1] Run `tests/contract/dataset_selector/test_selection.py` (T010–T013) and confirm all pass against the real `data/briefings/orcamentos-aeb-csv.md` and `data/datasets/orcamentos-aeb-csv/` data

**Checkpoint**: At this point, User Story 1 is fully functional and independently testable — `select_dataset` can be called end-to-end and every call is logged

---

## Phase 4: User Story 2 - Locate a dataset's files from its briefing key (Priority: P2)

**Goal**: Given a dataset briefing's file name, resolve that name to the location of the corresponding dataset's data files, using the isolated test fixtures (not the single real dataset), so the key→folder convention is verified independent of today's one registered dataset.

**Independent Test**: Take the known briefing file name `orcamentos-aeb-csv` (and the isolated fixture key `sample-key`) and verify it resolves to the matching folder under the datasets directory.

### Tests for User Story 2 ⚠️

> Write these tests FIRST, ensure they FAIL before implementation

- [X] T021 [P] [US2] Contract test for Acceptance Scenario 1 in `tests/contract/dataset_selector/test_selection.py`: given the briefing file `orcamentos-aeb-csv.md`, `LocalDatasetLocator("data/datasets").locate("orcamentos-aeb-csv")` returns the path to the `orcamentos-aeb-csv` folder under the datasets directory (contracts/selection.md US2 Acceptance Scenario 1)
- [X] T022 [P] [US2] Unit test for `LocalDatasetLocator` in `tests/unit/dataset_selector/test_locator.py`, using the `tests/fixtures/dataset_selector/datasets/sample-key/` fixture (T003): `locate("sample-key")` returns the fixture folder's path; `locate("does-not-exist")` raises `DatasetNotFoundError` carrying `key == "does-not-exist"` (data-model.md Errors table, FR-005; quickstart.md Scenario 4)
- [X] T023 [P] [US2] Unit test for `FileBriefingSource` in `tests/unit/dataset_selector/test_briefing.py`, using the `tests/fixtures/dataset_selector/briefings/sample-key.md` fixture (T003): `list_keys()` returns `["sample-key"]`; `get("sample-key")` returns the fixture file's exact text content; `get("missing-key")` raises `BriefingNotFoundError` carrying `key == "missing-key"`
- [X] T024 [P] [US2] Unit test for `JsonlSelectionLogger` in `tests/unit/dataset_selector/test_usage_log.py`, using a temp path: `log(entry)` appends exactly one JSON line per call (multiple calls produce multiple lines, one per call — FR-007); the file's parent directory is created on first use if it doesn't already exist; each appended line round-trips via `json.loads` back into the same `question`/`dataset_key`/`timestamp` values as the logged `DatasetSelectionLogEntry`

### Implementation for User Story 2

- [X] T025 [US2] Verify `LocalDatasetLocator` (T015) and `FileBriefingSource` (T014) satisfy the US2 tests as-is (both were already implemented generically in Phase 3, keyed off `list_keys()`/folder-name lookup rather than any hardcoded dataset name — no dataset-specific code path exists to add here); fix any gap the T021–T024 tests surface without introducing dataset-specific logic (research.md §3–§5)

**Checkpoint**: User Stories 1 AND 2 both work independently; the key→folder convention is verified against both the real dataset and isolated fixtures

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Type checking and CI wiring — part of this feature's definition of done (plan.md Constitution Check, Principle IX)

- [X] T026 [P] Run `pyright src/` and fix any type errors in `src/dataset_selector/` (plan.md Testing section; Eng. Principle 10)
- [X] T027 [P] Confirm `.github/workflows/ci.yml`'s existing `pytest tests/contract tests/unit -v` and `pyright src/` steps pick up the new `tests/contract/dataset_selector/`, `tests/unit/dataset_selector/`, and `src/dataset_selector/` paths with no config changes needed (they use directory-wide globs already covering `001-data-access-tools`); update the workflow only if it does not
- [X] T028 Run the full quickstart.md validation end-to-end (`pytest tests/contract/dataset_selector -v`, `pytest tests/unit/dataset_selector -v`, `pyright src/`) and confirm all scenarios in quickstart.md pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001) completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) completion
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) completion; its implementation task (T025) depends on User Story 1's implementation (T014, T015) already existing, since both stories share the same `LocalDatasetLocator`/`FileBriefingSource` classes — no separate implementation is needed, only additional verification
- **Polish (Phase 5)**: Depends on Phases 3 and 4 being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — the MVP
- **User Story 2 (P2)**: Reuses US1's `LocalDatasetLocator`/`FileBriefingSource` implementations directly (by design — data-model.md's Protocols are shared, not duplicated); its tests can be written in parallel with US1's, but T025 (its "implementation" checkpoint) is only meaningful once T014/T015 exist

### Within Each User Story

- Tests (T010–T013, T021–T024) MUST be written and FAIL before their corresponding implementation tasks
- Protocols (Phase 2) before implementations (Phase 3)
- `FileBriefingSource`/`LocalDatasetLocator`/`JsonlSelectionLogger` (T014–T016) before `StaticDatasetSelector` (T017)
- `StaticDatasetSelector` (T017) before `select_dataset` (T018)
- `select_dataset` (T018) before the package's public exports (T019)

### Parallel Opportunities

- T002, T003 (Setup) can run in parallel
- T004–T009 (all of Foundational — exceptions, models, and all four Protocol definitions in separate files) can all run in parallel
- T010–T013 (all US1 contract tests, same file but independent test functions) can be drafted in parallel, then run together
- T021–T024 (all US2 tests, four separate files) can run in parallel
- T026, T027 (Polish) can run in parallel

---

## Parallel Example: Foundational Phase

```bash
Task: "Create DatasetSelectorError, DatasetNotFoundError, BriefingNotFoundError, NoBriefingsAvailableError in src/dataset_selector/exceptions.py"
Task: "Create DatasetSelectionResult and DatasetSelectionLogEntry pydantic models in src/dataset_selector/models.py"
Task: "Define DatasetLocator Protocol in src/dataset_selector/locator.py"
Task: "Define BriefingSource Protocol in src/dataset_selector/briefing.py"
Task: "Define SelectionLogger Protocol in src/dataset_selector/usage_log.py"
Task: "Define DatasetSelector Protocol in src/dataset_selector/selector.py"
```

## Parallel Example: User Story 2 Tests

```bash
Task: "Contract test for US2 Acceptance Scenario 1 in tests/contract/dataset_selector/test_selection.py"
Task: "Unit test for LocalDatasetLocator in tests/unit/dataset_selector/test_locator.py"
Task: "Unit test for FileBriefingSource in tests/unit/dataset_selector/test_briefing.py"
Task: "Unit test for JsonlSelectionLogger in tests/unit/dataset_selector/test_usage_log.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run `tests/contract/dataset_selector/test_selection.py` (Scenarios 1, 2, and the logging/error edge cases) independently
5. `select_dataset` is now usable end-to-end by the agent's future wiring layer

### Incremental Delivery

1. Complete Setup + Foundational → Protocols/models/exceptions ready
2. Add User Story 1 → validate independently → MVP: `select_dataset` fully functional
3. Add User Story 2 → validate independently → key→folder convention formally verified via isolated fixtures, no regressions to US1
4. Add Polish → pyright clean, CI confirmed, quickstart.md fully green

## Notes

- [P] tasks = different files (or independent test functions), no dependencies
- [Story] label maps task to specific user story for traceability
- Verify tests fail before implementing (contract tests in T010–T013 and T021–T024 must fail against a no-op/absent implementation first)
- Commit after each task or logical group
- Stop at each checkpoint to validate story independently
- No dataset-specific facts (e.g. the literal string `"orcamentos-aeb-csv"`) may appear inside `src/dataset_selector/selector.py`, `locator.py`, or `briefing.py` — only in tests and fixtures (Constitution Principle V, research.md §3)
