---

description: "Task list for 009 Forgiving Text Matching and Value Suggestions"
---

# Tasks: Forgiving Text Matching and Value Suggestions

**Input**: Design documents from `/specs/009-text-value-matching/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. The plan (Testing section) and Constitution Principles IV and IX require
unit and contract tests for every contract row. Existing suites `tests/contract/data_access/test_query.py`,
`tests/contract/data_access/test_aggregation.py` and `tests/unit/data_access/test_query_engine.py`
MUST pass **unedited** (SC-006). `tests/contract/data_access/test_inspection.py` only gains cases.

**Live model**: every task that needs a real model uses the local vLLM target
`Qwen/Qwen3-8B-AWQ` at `http://localhost:8000/v1` (`--api-key x`). The web UI, if used,
must run with `--port 8001` because vLLM holds port 8000.

**Organization**: Tasks are grouped by user story so each story can be implemented and
tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Single project: `src/` and `tests/` at the repository root (plan.md "Project Structure").

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Versioned stopword artifact, packaging and the shared test fixture.

- [X] T001 Create the versioned Portuguese stopword list `src/data_access/stopwords/pt_v1.txt` (UTF-8, one word per line, blank lines and lines starting with `#` ignored; a header comment says named versions are never edited in place and a changed list is a new file `pt_v2.txt`). Contents (research.md R3): articles `a o as os um uma uns umas`; prepositions and contractions `de do da dos das em no na nos nas num numa dum duma ao aos à às por pelo pela pelos pelas para pra com sem sob até`; conjunctions `e ou nem mas que`.
- [X] T002 [P] Make `src/data_access/stopwords/*.txt` ship as package data in `pyproject.toml` (add a `[tool.setuptools.package-data]` entry `data_access = ["stopwords/*.txt"]`; check how `src/qa_agent/prompts/*.md` is shipped and follow the same approach, adding its entry too if missing). Confirm with `pip install -e ".[dev]"` that the file is readable via `importlib.resources.files("data_access") / "stopwords" / "pt_v1.txt"`.
- [X] T003 [P] Create fixture `tests/fixtures/data_access/sample_dataset/budget_actions.csv` with columns `nome_unidade,nome_programa,nome_acao,data_ano,valor_pago` and ~25 rows designed so every contract row can be hand-computed: `nome_unidade` values "Agência Espacial Brasileira" (majority of rows) and "Ministério da Ciência, Tecnologia, Inovações e Comunicações"; `nome_acao` values including "Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS-3", "Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS-4", "Projeto CBERS-4", "Projeto CBERS-4A", "Projeto CBERS-14", "Desenvolvimento do Satélite Amazônia-1", "Programa X", "PROGRAMA X", "Nº 5 – 10%", "...", a value containing "2014", and at least 2 empty/whitespace cells (missing); `nome_programa` with more than 3 distinct values for threshold tests; `data_ano` with a field whose second distinct value does **not** appear in the first 20 rows (US3-AS1, since `SAMPLE_SIZE_CAP` samples the head). Put the second `nome_unidade` value only in rows after row 20. Verify `tests/contract/data_access/test_discovery.py` still passes (it checks membership only).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The pure matching module and config that all three stories use.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Create `src/data_access/text_matching.py` (no `pydantic_ai` or `qa_agent` import; module docstring explains the rules and links research.md R1–R4) with:
  - `TextMatchingConfig`: frozen pydantic model, fields `value_list_threshold: int = 30` (`ge=0`; "A field is listed when `distinct_count <= value_list_threshold`. `0` lists nothing."), `max_suggestions: int = 5` (`ge=1`), `stopwords: str = "pt_v1"` (validator: "Must name a file `data_access/stopwords/<name>.txt`. Validated on construction." — raise a validation error for unknown names).
  - `load_stopwords(name) -> frozenset[str]`: reads `stopwords/<name>.txt` via `importlib.resources`, skips blank and `#` lines, normalizes each word with `normalize`, cached per name (`functools.cache`).
  - `normalize(text) -> str`: `unicodedata.normalize("NFKD", text)`, drop chars where `unicodedata.combining(c)`, `casefold()`, replace each run of `[\W_]+` with a space, then `" ".join(s.split())`.
  - `MatchRules`: frozen dataclass with `stopwords: frozenset[str]`, `MatchRules.from_config(config)`, and methods `words(text)`, `query_words(value)` (words minus stopwords, or all words if that leaves none), `acronym(text)` (first letter of each non-stopword word, joined; `""` if none), `equals(stored, value)` (`normalize(stored) == normalize(value)`, no stopword removal), `contains(stored, value)` (every query word is a prefix of some word of `stored`, any order; `True` when there are no query words), `overlap(stored, value)` (count of query words that are a prefix of some word of `stored` or of `acronym(stored)`; acronym skipped when `""`).
  - `rank_candidates(value_counts: Mapping[str, int], value: str, rules: MatchRules, limit: int) -> list[tuple[str, int, int]]` returning `(value, overlap, row_count)` for `overlap >= 1`, sorted by overlap desc, row_count desc, value asc (code point), first `limit`. Callers pass only non-missing values.
- [X] T005 [P] Write unit tests in `tests/unit/data_access/test_text_matching.py`, one test per row of the "Normalization" and "Behavioral requirements" tables in `specs/009-text-value-matching/contracts/text-matching.md` at the function level (e.g. `normalize("  Satélite   Sino-Brasileiro (CBERS) ") == "satelite sino brasileiro cbers"`, `"-"`/`"..."` → `""`, `contains("2014", "4")` is False, `contains("Projeto CBERS-4A", "cbers 4")` is True, `contains("Desenvolvimento", "de")` is True, `"Nº 5 – 10%"` equals itself), plus: `acronym("Agência Espacial Brasileira") == "aeb"`, `acronym("Ministério da Ciência, Tecnologia, Inovações e Comunicações") == "mctic"`, `overlap("Agência Espacial Brasileira", "AEB") == 1`, `rank_candidates` ordering and tie-breaks (overlap, then row_count, then code point) and `limit`, `load_stopwords("pt_v1")` contains `"a"` (from "à") and `"ate"` (from "até"), `TextMatchingConfig(stopwords="nope")` raises `pydantic.ValidationError`, `TextMatchingConfig(max_suggestions=0)` and `value_list_threshold=-1` raise. Name tests after the scenario ids (US1-AS1, Clarif-Q1, Edge-…).
- [X] T006 Change `PandasQueryEngine` in `src/data_access/query_engine.py` to take `rules: MatchRules` in `__init__` (default `MatchRules.from_config(TextMatchingConfig())` so existing `PandasQueryEngine()` calls in `tests/unit/data_access/test_query_engine.py` keep working unedited). The `QueryEngine` protocol signatures stay unchanged (Eng. 2). Update the class docstring.
- [X] T007 Replace the module-level `_ENGINE = PandasQueryEngine()` in `src/data_access/capabilities.py` with an engine built per call from a `text_matching: TextMatchingConfig = TextMatchingConfig()` keyword-only argument added to `inspect_schema`, `query_rows` and `aggregate_rows` (Eng. 4). Behavior is unchanged in this task; later tasks use the argument. Run `pytest tests/contract/data_access tests/unit/data_access` to confirm nothing broke.

**Checkpoint**: `pytest tests/unit/data_access/test_text_matching.py` passes, existing data access suites pass, `pyright src/` clean.

---

## Phase 3: User Story 1 - Text filters tolerate differences in writing (Priority: P1) 🎯 MVP

**Goal**: `equals`/`contains` in `query_rows` and `aggregate_rows` filters ignore case, accents, hyphens and punctuation, and `contains` skips stopwords and matches word starts in any order.

**Independent Test**: `pytest tests/contract/data_access/test_text_matching_filters.py` — filters on `budget_actions.csv` return the hand-computed row sets through both `query_rows` and `aggregate_rows`.

### Tests for User Story 1 ⚠️

> Write these tests first and check they FAIL before T009.

- [X] T008 [P] [US1] Write contract tests in `tests/contract/data_access/test_text_matching_filters.py` against fixture `budget_actions.csv`, through the public `data_access.capabilities.query_rows` and `aggregate_rows` (count per `nome_unidade`/`nome_acao` with the same filters), one test per row of the traceability table in `specs/009-text-value-matching/contracts/text-matching.md`: US1-AS1..AS5, US1-AS6 (range filter unchanged), US1-AS7 (an exact stored value matches the same rows as before), Clarif-Q1 (`contains "satel"` matches; `contains "4"` does not match the "2014" value; `contains "cbers 4"` does not match "Projeto CBERS-14" but matches "Projeto CBERS-4A"), Edge (`contains "de"`, `contains "..."` matches every non-missing value, `equals "-"` matches "..." but not missing cells, `equals "programa x"` matches both "Programa X" and "PROGRAMA X", `equals "2012"` on `data_ano`, "Nº 5 – 10%" matches itself). Assert returned rows hold raw stored values (FR-006). Add one test named for the **deliberate change**: `equals ""` and `contains ""` no longer match missing cells (contracts/text-matching.md, last paragraph).

### Implementation for User Story 1

- [X] T009 [US1] Implement normalized matching in `PandasQueryEngine._condition_mask` in `src/data_access/query_engine.py`: for `EqualsCondition` and `ContainsCondition`, build a dict over `column.unique()` mapping each value to `False` if `_is_missing(value)` else `self._rules.equals/contains(str(value), condition.value)`, then return `column.map(that_dict).astype(bool)` (research.md R2: each distinct string normalized once per condition). `RangeCondition` stays byte-identical (FR-007). Update the `_condition_mask` docstring with the rule and the missing-values change.
- [X] T010 [US1] Add `Field(description=…)` to `EqualsCondition.value` and `ContainsCondition.value` in `src/data_access/models.py` with the short form of the rule (equals: "Whole value, compared ignoring case, accents and punctuation"; contains: "Every word (filler words like 'de', 'do' skipped) must start a word of the stored value, in any order; case, accents and punctuation ignored"). Types, discriminator and validation unchanged.
- [X] T011 [US1] Run `pytest tests/contract/data_access tests/unit/data_access -v` and `pyright src/`; T008 passes and `test_query.py`, `test_aggregation.py`, `test_query_engine.py` pass with no edits (`git diff --stat main -- tests/contract/data_access/test_query.py tests/contract/data_access/test_aggregation.py tests/unit/data_access/test_query_engine.py` is empty). If an existing test relied on `equals ""`/`contains ""` matching missing cells, stop and report it instead of editing the test.

**Checkpoint**: US1 works on its own. The "Amazônia-1" failure from 008 now matches (quickstart §2 second line).

---

## Phase 4: User Story 2 - A zero-row result suggests the closest real values (Priority: P2)

**Goal**: an empty `query_rows`/`aggregate_rows` result carries `value_suggestions` for each text condition that matches nothing on its own, ranked by word-start overlap including acronyms.

**Independent Test**: `pytest tests/contract/data_access/test_value_suggestions.py` — each zero-row filter on `budget_actions.csv` yields the expected suggestions, in order, for the expected field.

### Tests for User Story 2 ⚠️

- [X] T012 [P] [US2] Write contract tests in `tests/contract/data_access/test_value_suggestions.py` against `budget_actions.csv`, one test per row of the traceability table in `specs/009-text-value-matching/contracts/value-suggestions.md`: US2-AS1 (`nome_unidade equals "AEB"` → first candidate "Agência Espacial Brasileira", `overlap=1`), US2-AS2 (`contains "satélite CBERS 5"` ordering by overlap), US2-AS3 (only the non-matching condition gets an entry), US2-AS4 (`value_suggestions == []` and key present in `model_dump_json()`), US2-AS5 (`candidates == []`), US2-AS6 (non-empty result: `"value_suggestions"` not in `model_dump_json()`), US2-AS7 (range-only 0 rows: key absent), FR-011 (exactly `max_suggestions` candidates when more overlap, using `TextMatchingConfig(max_suggestions=2)`; ties by `row_count` desc then code point), Edge (missing values never candidates; `aggregate_rows` with 0 groups gives the same entries as `query_rows` with the same filters). Also assert each `ValueSuggestion` carries `field`, `op` and the `value` as sent (FR-012) and that candidate values are raw stored spellings (FR-006).

### Implementation for User Story 2

- [X] T013 [US2] Add to `src/data_access/models.py`: `SuggestedValue` (`value: str`; `overlap: int` `ge=1`; `row_count: int` `ge=1`), `ValueSuggestion` (`field: str`; `op: Literal["equals", "contains"]`; `value: str`; `candidates: list[SuggestedValue]`, docstring: "At most `max_suggestions`. Ordered by `overlap` desc, `row_count` desc, `value` asc (code point). **Empty** means 'no close values found'"), and `value_suggestions: list[ValueSuggestion] | None = Field(default=None, exclude_if=lambda v: v is None)` on `RowQueryResult` and `AggregationResult`, so results without suggestions serialize exactly as before (FR-013).
- [X] T014 [US2] Implement suggestions in `src/data_access/capabilities.py`: a private helper `_value_suggestions(df, conditions, engine, rules, max_suggestions) -> list[ValueSuggestion] | None` that returns `None` when there are no `equals`/`contains` conditions; otherwise, in request order, runs `engine.query_rows(df, [condition])` on the **unfiltered** source for each text condition, skips conditions that match ≥1 row, and for the rest builds `value_counts` from `df[field]` excluding missing values (`_is_missing`), calls `rank_candidates(..., limit=max_suggestions)` and wraps the result in `ValueSuggestion`/`SuggestedValue`. Call it from `query_rows` only when `total_match_count == 0` and from `aggregate_rows` only when `total_group_count == 0`, after all existing validation (errors raised exactly as before, same order). Reuse the `df` already read (no second read). Update the docstrings of both capabilities.
- [X] T015 [US2] Run `pytest tests/contract/data_access tests/unit/data_access -v` and `pyright src/`; T012 passes, earlier suites still pass unedited.

**Checkpoint**: US1 and US2 work. On the real dataset `equals "AEB"` on `nome_unidade` yields "Agência Espacial Brasileira" at rank 1 (SC-002).

---

## Phase 5: User Story 3 - Schema inspection lists every value of low-cardinality fields (Priority: P3)

**Goal**: `inspect_schema` reports `distinct_count` for every field (whole source) and the full raw `values` list when `distinct_count <= value_list_threshold`.

**Independent Test**: new cases in `tests/contract/data_access/test_inspection.py` pass on `budget_actions.csv`; existing cases pass unedited.

### Tests for User Story 3 ⚠️

- [X] T016 [P] [US3] Add cases (do not edit existing ones) to `tests/contract/data_access/test_inspection.py`, one per row of the traceability table in `specs/009-text-value-matching/contracts/schema-inspection.md`: US3-AS1 (`nome_unidade` lists both values though only one is in the sample), US3-AS2 (field with exactly `threshold` distinct values — use `TextMatchingConfig(value_list_threshold=N)` matching a fixture field — lists all, code-point order, raw spelling), US3-AS3 (`threshold + 1` → `values is None`, `distinct_count == threshold + 1`), US3-AS4 (empty/whitespace cells not listed or counted), US3-AS5 (`identifier`, `fields[].name/type`, `sample` equal to the output with the new fields removed; compare against a customers.csv expectation already used by existing tests), Edge ("Programa X" and "PROGRAMA X" are two entries; `value_list_threshold=0` → every `values is None`), invariants (`values is None` ⇔ `distinct_count > value_list_threshold`; `len(values) == distinct_count` when listed) and `result.value_list_threshold` equals the config value.

### Implementation for User Story 3

- [X] T017 [US3] Extend `src/data_access/models.py`: `FieldInfo.distinct_count: int` ("Distinct non-missing raw values of this field across the **whole** source") and `FieldInfo.values: list[str] | None` ("All those values, raw, sorted by code point, when `distinct_count <= value_list_threshold`. Otherwise `null` (not listed: too many values)"); `SchemaInspectionResult.value_list_threshold: int`. No existing field removed, renamed or retyped.
- [X] T018 [US3] Implement in `inspect_schema` in `src/data_access/capabilities.py`: keep field selection, order, `type` and `sample` exactly as today (FR-017); for each reported field compute the distinct non-missing raw values over **all** rows (`_is_missing` rule), set `distinct_count`, set `values = sorted(distinct)` when `distinct_count <= text_matching.value_list_threshold` else `None`, and set `value_list_threshold`. No length or size cap (FR-014). Update the docstring.
- [X] T019 [US3] Run `pytest tests/contract/data_access tests/unit/data_access -v` and `pyright src/`; T016 passes and existing inspection cases pass unedited.

**Checkpoint**: all three stories work at the data access layer (quickstart §2 prints the expected output).

---

## Phase 6: Agent Wiring, Tool Descriptions and Run Records (FR-016, FR-018)

**Purpose**: carry `TextMatchingConfig` from settings to tools, state the new behavior in tool descriptions, and record it on runs. Spans all stories; depends on Phases 3–5.

### Tests ⚠️

- [X] T020 [P] Extend `tests/unit/qa_agent/test_tools_description.py` (keep every existing 007 assertion): via the captured `ToolDefinition`s, assert `query_rows` description mentions ignoring case, accents and punctuation, `equals` comparing the whole value, `contains` needing every word (filler words like "de"/"do" skipped) to start a word of the value in any order, and `value_suggestions` on 0-row results; `aggregate_rows` states the same filter and suggestion facts; `inspect_schema` mentions `distinct_count`, `values` and `value_list_threshold` and that listed values can be used in filters; the `value` property of the equals/contains condition schemas has a description (contracts/agent-tools-and-runs.md table).
- [X] T021 [P] Extend `tests/contract/testset_runner/test_run_testset.py` and `tests/contract/testset_runner/test_run_conversations.py`: `run_testset(..., text_matching=TextMatchingConfig())` / `run_conversations(..., text_matching=...)` record the value, it round-trips through the store, and calls without it record `None`. Extend `tests/unit/testset_runner/test_store.py`: `tests/fixtures/testset_runner/pre-006-run.json` still loads with `text_matching is None`. Add a check that `compare` does not reject two runs that differ only in `text_matching`.

### Implementation

- [X] T022 [P] Add `text_matching: TextMatchingConfig = Field(default_factory=TextMatchingConfig)` to `AgentSettings` in `src/qa_agent/settings.py` and `text_matching: TextMatchingConfig = field(default_factory=TextMatchingConfig)` to the `AgentDeps` dataclass in `src/qa_agent/deps.py`. No new env var or CLI flag (research.md R6).
- [X] T023 Build `AgentDeps(..., text_matching=settings.text_matching)` in `_answer_with_selection` in `src/qa_agent/capabilities.py`; add a `text_matching: TextMatchingConfig = TextMatchingConfig()` constructor parameter and read-only `text_matching` property to `QaAgentQuestionAnswerer` in `src/qa_agent/answerer.py`, passed into the settings it uses (same pattern as `history_char_limit`).
- [X] T024 Update `src/qa_agent/tools.py`: the `inspect_schema`, `query_rows` and `aggregate_rows` wrappers pass `text_matching=ctx.deps.text_matching` to their capabilities (signatures, budget and error handling unchanged); add/extend docstrings per research.md R7 with every fact in the contracts/agent-tools-and-runs.md "Descriptions the model sees" table. Do **not** edit `src/qa_agent/prompts/system_v1.md` or `system_v2.md` and add no prompt version.
- [X] T025 [P] Add `text_matching: TextMatchingConfig | None = None` (`None` = pre-009 run) to `TestRun` in `src/testset_runner/models.py` and `ConversationRun` in `src/testset_runner/conversation_models.py`; make sure `src/testset_runner/comparator.py` does not treat a `text_matching` difference as incompatible.
- [X] T026 Add `text_matching: TextMatchingConfig | None = None` to `run_testset` in `src/testset_runner/runner.py` and `run_conversations` in `src/testset_runner/conversation_runner.py`, stored on the run. In `src/testset_runner/cli.py`, pass `answerer.text_matching` for both `run` and `run-conversations` and print, right after the retry policy line, `Text matching: value_list_threshold=30, max_suggestions=5, stopwords=pt_v1` (values from the run; `Text matching: not recorded` when `None`).
- [X] T027 Run the full offline gate: `pytest tests/contract tests/unit -v` and `pyright src/`. `tests/contract/qa_agent/test_standalone_unchanged.py` and `tests/unit/qa_agent/test_prompt_loader.py` pass unedited; `git diff --stat main -- src/qa_agent/prompts` is empty.

**Checkpoint**: offline track of quickstart §1 is green.

---

## Phase 7: Polish, Live Evaluation and Results (FR-019, SC-002–SC-005)

**Purpose**: mechanism check on the real dataset, the before/after live evaluation against Qwen3-8B on vLLM port 8000, and the results record.

- [X] T028 Run quickstart §2 (the inline Python block in `specs/009-text-value-matching/quickstart.md`) against `data/datasets/orcamentos-aeb-csv`, and confirm: `AEB` → 0 rows, first candidate "Agência Espacial Brasileira"; Amazônia-1 → matches directly, no suggestions; `satélite CBERS 3` → matches the CBERS-3 rows; `nome_unidade` (2), `nome_programa` (13), `data_ano` (20) fully listed, `nome_acao` (116) and monetary fields `None` (SC-002, SC-003). Keep the output for results.md.
- [X] T029 [P] Write `specs/009-text-value-matching/analyze_runs.py` (same style as `specs/008-chat-conversation-history/build_conversation_testset.py`; CLI `--before <run-id> --after <run-id>`, reads only recorded files in `data/conversation_runs/`) that prints: (1) per-category scored-turn rates before/after and per-turn status transitions joined by `(conversation_id, turn_index)`; (2) for the after run, every `query_rows`/`aggregate_rows` step with an empty result: its text conditions, whether the value exists in the source (using `MatchRules` on the real source), whether `value_suggestions` were returned, and whether the next step used a suggested value; (3) `len(inspect_schema(ds, "dados_gerais/tb_geral.csv").model_dump_json())` after, and before (same result dumped without `distinct_count`, `values`, `value_list_threshold`; expected 5,994 chars). Check the before run `20260925T095751382002Z` file exists first.
- [X] T030 Live conversation run (needs the model; confirm `curl -s http://localhost:8000/v1/models` lists `Qwen/Qwen3-8B-AWQ` first): `python -m testset_runner.cli run-conversations --testset data/testsets/conversations/orcamentos-aeb-csv-conversations.json --model Qwen/Qwen3-8B-AWQ --base-url http://localhost:8000/v1 --api-key x --max-attempts 3 --history-char-limit 16000`. Check the report ends with the `Text matching: …` line. Record the run id.
- [X] T031 Live standalone run (needs the model): `python -m testset_runner.cli run --testset data/testsets/orcamentos-aeb-csv-10.json --model Qwen/Qwen3-8B-AWQ --base-url http://localhost:8000/v1 --api-key x --max-attempts 3`, then `python -m testset_runner.cli compare 20260925T100203429266Z <new-run-id>` (SC-005: 0 `newly_failing`). Record the run id and compare output.
- [X] T032 Run `python specs/009-text-value-matching/analyze_runs.py --before 20260925T095751382002Z --after <T030 run id>` and keep the output.
- [X] T033 Write `specs/009-text-value-matching/results.md` (same structure as `specs/008-chat-conversation-history/results.md`): target and settings, both run ids and baselines, the mechanism check from T028, the per-category and per-turn tables and zero-row audit from T032, the `compare` output from T031, the `inspect_schema` size before/after, each of SC-001–SC-006 reported as met / not met with the evidence, and an explicit caveat that one run per side is noisy for small categories (e.g. the 3 `follow-up-metric` conversations). If a remaining failure points at a prompt change, note it as a separate follow-up, not part of this feature.
- [X] T034 [P] Documentation pass: docstrings in `src/data_access/text_matching.py`, `src/data_access/query_engine.py` and `src/data_access/capabilities.py` describe the rules and link the 009 contracts (Principle III); add a `budget_actions.csv` line to `tests/fixtures/data_access/sample_dataset/README.md` explaining what the fixture exercises.
- [ ] T035 Optional web UI spot check (needs the model): `python -m web_ui.cli --port 8001`, ask "Quanto foi pago pela AEB em 2012?", and check the trace shows a matching filter or a 0-row result with `value_suggestions` followed by a retry with "Agência Espacial Brasileira". Note the outcome in results.md.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: T004 needs T001 (and T002 for packaging); T006–T007 need T004. Blocks all stories.
- **US1 (Phase 3)**: after Phase 2.
- **US2 (Phase 4)**: after Phase 2. Uses the normalized engine from T009 for the per-condition check, so do it after US1 (its contract tests assume normalized matching, e.g. "AEB" only gets suggestions because nothing matches after normalization).
- **US3 (Phase 5)**: after Phase 2 only; independent of US1/US2 (different functions, but shares `models.py`/`capabilities.py`, so do not run in parallel with T013/T014 in one working tree).
- **Wiring (Phase 6)**: after Phases 3–5 (descriptions must describe implemented behavior).
- **Polish/Evaluation (Phase 7)**: after Phase 6. T030/T031 need the vLLM server on port 8000.

### User Story Dependencies

- **US1 (P1)**: no dependency on other stories.
- **US2 (P2)**: builds on US1's normalized matcher (spec: "It builds on US1").
- **US3 (P3)**: independent of US1 and US2.

### Within Each Story

- Tests first, check they fail, then models, then capabilities, then the run of the suite.

### Parallel Opportunities

- T002 and T003 in parallel with T001.
- T005 in parallel with T006/T007 once T004 exists.
- T008, T012 and T016 (test files) can be written in parallel with each other.
- T020, T021, T022 and T025 touch different files and can run in parallel.
- T029 can be written while T030/T031 run the model.

---

## Parallel Example: User Story 1

```bash
# While the matcher is being wired into the engine (T009):
Task: "Contract tests in tests/contract/data_access/test_text_matching_filters.py (T008)"
Task: "Field descriptions on EqualsCondition/ContainsCondition in src/data_access/models.py (T010)"
```

## Parallel Example: Phase 6

```bash
Task: "Tool description assertions in tests/unit/qa_agent/test_tools_description.py (T020)"
Task: "Run-record tests in tests/contract/testset_runner/ (T021)"
Task: "AgentSettings/AgentDeps fields in src/qa_agent/settings.py and deps.py (T022)"
Task: "TestRun/ConversationRun fields in src/testset_runner/models.py and conversation_models.py (T025)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 + Phase 2.
2. Phase 3 (US1). This alone fixes the 008 Amazônia-1 case-only mismatch.
3. **Stop and validate**: `pytest tests/contract/data_access`, quickstart §2 Amazônia-1 line.

### Incremental Delivery

1. Setup + Foundational → matcher ready.
2. US1 → forgiving filters (MVP).
3. US2 → suggestions bridge abbreviations ("AEB").
4. US3 → value lists prevent the failure up front.
5. Phase 6 → the agent sees the new behavior and runs record the config.
6. Phase 7 → one live run per test set on Qwen3-8B (vLLM :8000) and results.md.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks.
- Existing tests in `test_query.py`, `test_aggregation.py`, `test_query_engine.py` must not be edited (SC-006); if one fails, report it.
- `data_access` must never import `pydantic_ai` or `qa_agent` (Eng. 1).
- Prompts `system_v1.md` / `system_v2.md` stay byte-identical (FR-018).
- Commit after each phase checkpoint.
