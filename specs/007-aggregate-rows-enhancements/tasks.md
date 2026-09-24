---

description: "Task list for 007 Richer Aggregation (Filters, Functions, Ordering, Limit)"
---

# Tasks: Richer Aggregation (Filters, Functions, Ordering, Limit)

**Input**: Design documents from `/specs/007-aggregate-rows-enhancements/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/aggregation.md, contracts/aggregate-rows-tool.md, quickstart.md

**Tests**: Included. The plan (Constitution Principle IV) requires one contract test per acceptance scenario, named `test_007_us<N>_<M>_...`, with hand-computed expected literals (SC-002). Two new unit-test files are also required: engine ordering and the tool description.

**Organization**: Tasks are grouped by user story, so each story can be implemented and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: The user story the task belongs to (US1, US2, US3)
- All paths are relative to the repository root (single project, `src/` layout)

## Shared test fixture (reference for every contract test below)

T001 creates `tests/fixtures/data_access/sample_dataset/transfers.csv` (identifier `transfers.csv`). CSV sources are read with `na_filter=False`, so an empty cell arrives as `""`. `""` counts as **missing** (research.md §4) and is still reported as `""` in `group_values`.

| row | ano | orgao | uf | mes | valor | fornecedor |
|-----|-----|-------|----|-----|-------|------------|
| r1 | 2022 | MS | SP | 1 | `1.000,00` | Alfa |
| r2 | 2022 | MS | RJ | 2 | `500,00` | Beta |
| r3 | 2023 | MS | SP | 1 | `10` | Alfa |
| r4 | 2023 | MS | SP | 2 | `20` | Beta |
| r5 | 2023 | MS | RJ | 10 | `30` | Alfa |
| r6 | 2023 | ME | SP | 2 | `1.234,56` | Alfa |
| r7 | 2023 | ME | SP | 10 | `n/d` | *(empty)* |
| r8 | 2023 | ME | MG | 1 | `2.000,00` | Gama |
| r9 | 2022 | ME | MG | 2 | `2.000,00` | Gama |
| r10 | 2023 | MC | SP | 12 | *(empty)* | Alfa |
| r11 | 2022 | MC | RJ | 12 | `99,90` | Beta |
| r12 | 2023 | MC | MG | *(empty)* | `5,00` | Alfa |

Classification on the whole source (`is_numeric_like`, threshold 0.8, first 20 rows): `valor` is numeric-like (10/12 values parse), `mes` is numeric-like (11/12), `ano` is numeric-like, and `orgao` / `uf` / `fornecedor` are text.

Hand-computed values used by the tests:

- `sum_valor` by `orgao`, no filter: MS `1560.0`, ME `5234.56`, MC `104.9`.
- `sum_valor` by `orgao`, filter `ano equals "2023"`: MS `60.0`, ME `3234.56`, MC `5.0`.
- `sum_valor` by `orgao`, filters `ano equals "2023"` AND `uf equals "SP"`: MS `30.0`, ME `1234.56`, MC `0.0`.
- `sum_valor` by `orgao`, filters `ano equals "2023"` AND `valor range min=15`: exactly two groups, MS `50.0` and ME `3234.56` (no MC group).
- `mean`/`min`/`max` of `valor` by `orgao`, filter `ano equals "2023"`: MS `20.0`/`10.0`/`30.0`; ME `1617.28`/`1234.56`/`2000.0` (`n/d` skipped); MC `5.0`/`5.0`/`5.0` (the empty r10 is ignored, not counted as 0).
- `mean`/`min`/`max`/`sum` of `valor` by `orgao`,`uf`, filter `ano equals "2023"`: group (MC, SP) (r10 only) → `None`/`None`/`None`, and `sum` stays `0.0`.
- `count_distinct_fornecedor` by `uf`, filter `ano equals "2023"`: SP → `2` (Alfa, Beta, Alfa, missing, Alfa). `count_distinct_mes` by `orgao`, no filter: MS → `3` ("1","2","10"), ME → `3`, MC → `1` (only "12"; r12's `""` is missing).
- `count_ano` by `orgao`,`uf`, no filter: (MS,SP) 3; (MS,RJ) 2; (ME,SP) 2; (ME,MG) 2; (MC,SP) 1; (MC,RJ) 1; (MC,MG) 1 (7 groups).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: The shared fixture and the SC-004 baseline, both needed before any code changes.

- [X] T001 Create `tests/fixtures/data_access/sample_dataset/transfers.csv` with the header `ano,orgao,uf,mes,valor,fornecedor` and exactly rows r1–r12 from the "Shared test fixture" table above, in that order. Quote values that contain commas (for example `"1.000,00"`), and leave the cells marked *(empty)* empty (for example r10: `2023,MC,SP,12,,Alfa`). Don't edit `sample_dataset/README.md`. The discovery tests look up sources by identifier (`tests/contract/data_access/test_discovery.py`), so adding the file is safe.
- [X] T002 [P] Record the SC-004 **baseline** run at the pre-feature commit `6636991`, following quickstart.md §4 ("at the pre-feature commit"): `python -m testset_runner.cli run --testset data/testsets/orcamentos-aeb-csv.json`, then note the `--model` / `--base-url` / `--max-attempts` values used. Create `specs/007-aggregate-rows-enhancements/results.md` with a "Baseline" section: commit, run file path under `data/testset_runs/`, settings, overall and per-category match rates, and the question ids that need filtered / mean / min-max / distinct / top-N aggregation (research.md §10). Needs model credentials. It doesn't block any code task.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The result-shape change and the deduplicated numeric-classification helper that every story builds on.

**⚠️ CRITICAL**: No user-story work can begin until this phase is complete.

- [X] T003 In `src/data_access/models.py`, add two **required** fields to `AggregationResult`: `total_group_count: int` (groups after filtering and before the limit) and `truncated: bool` (`total_group_count > len(groups)`), in the style of `RowQueryResult` (data-model.md "AggregationResult", research.md §8). Give them no defaults.
- [X] T004 In `src/data_access/capabilities.py`, add the private helper `_is_numeric_field(df: pd.DataFrame, field: str) -> bool` that returns `is_numeric_like(df[field].head(SAMPLE_SIZE_CAP).tolist())` (research.md §2). Replace the inline copies with it in `_validate_filter_fields` (range check) and in `aggregate_rows` (the `sum` check), and in `inspect_schema` too if that keeps the same rule. `inspect_schema` samples `df.head(SAMPLE_SIZE_CAP)`, which is equivalent. Make both `AggregationResult(...)` constructions in `aggregate_rows` pass `total_group_count=len(groups)` and `truncated=False`. The empty-source early exit passes `total_group_count=0` and `truncated=False`.
- [X] T005 In `tests/contract/data_access/test_aggregation.py`, update the module docstring to reference both `001` US4 and `007` (`specs/007-aggregate-rows-enhancements/contracts/aggregation.md`). Add `FIXTURE_ID = "transfers.csv"`, a small helper `_by_group(result, key)` that maps a single-field group value to `results[key]`, and the test `test_007_result_reports_total_group_count_and_not_truncated_without_limit`: group `transfers.csv` by `orgao` with `count_ano`, then assert `total_group_count == 3`, `truncated is False` and `len(groups) == 3`. Also extend `test_us4_5_source_with_no_rows_returns_empty_groups` with `total_group_count == 0` and `truncated is False`. Don't change any existing assertion (SC-001).

**Checkpoint**: `pytest tests/contract/data_access/test_aggregation.py` and `pyright src/` pass. Existing behavior is unchanged except for the two new result fields.

---

## Phase 3: User Story 1 - Aggregate only the rows that match filters (Priority: P1) 🎯 MVP

**Goal**: `AggregationRequest.filters` (equals / contains / range, combined with AND) restricts which rows are grouped and aggregated, and is validated exactly like `query_rows`.

**Independent Test**: Aggregate `transfers.csv` with and without `ano equals "2023"` and compare against the hand-computed sums in the fixture section.

### Tests for User Story 1 ⚠️ (write first; they must fail before T010–T012)

- [X] T006 [US1] In `tests/contract/data_access/test_aggregation.py`, add `test_007_us1_1_filter_restricts_sum_to_matching_rows` (group `orgao`, `sum_valor`, `filters=[EqualsCondition(field="ano", value="2023")]` → MS `60.0`, ME `3234.56`, MC `5.0`, using `pytest.approx`) and `test_007_us1_6_no_filters_matches_unfiltered_behavior` (the same request without `filters` → MS `1560.0`, ME `5234.56`, MC `104.9`).
- [X] T007 [US1] In the same file, add `test_007_us1_2_multiple_filters_combined_with_and`. Case (a) uses `ano equals "2023"` AND `uf equals "SP"` → MS `30.0`, ME `1234.56`, MC `0.0`. Case (b) uses `ano equals "2023"` AND `RangeCondition(field="valor", min=15)` → exactly the groups {MS: `50.0`, ME: `3234.56`}. Add a check that the rows `query_rows(dataset, "transfers.csv", same_filters)` returns match the rows the aggregation grouped (compare the `count_ano` total to `total_match_count`), so filter semantics can't drift from row queries (FR-001).
- [X] T008 [US1] In the same file, add:
  - `test_007_us1_3_filters_matching_nothing_return_zero_groups`: `ano equals "1999"` → `groups == []`, `total_group_count == 0`, `truncated is False`, no error.
  - `test_007_us1_4_unknown_filter_field_raises_field_not_found`: `EqualsCondition(field="nope", value="x")` → `FieldNotFoundError` with `.field == "nope"`.
  - `test_007_us1_5_range_filter_on_text_field_raises_numeric_type_error`: `RangeCondition(field="fornecedor", min=1)` → `NumericTypeError` with `.field == "fornecedor"`.
  - `test_007_us1_5_range_filter_validated_even_on_empty_source` (uses `tmp_path`, a CSV with header `a,b` and no rows, and a range filter on `b` → `NumericTypeError`, the same as `query_rows` today; research.md §3).

### Implementation for User Story 1

- [X] T009 [US1] In `src/data_access/models.py`, add `filters: list[FilterCondition] = Field(default_factory=list, description=...)` to `AggregationRequest`. The description says the conditions are the same as `query_rows` (equals / contains / range), are combined with AND, and are applied **before** grouping (FR-017).
- [X] T010 [US1] In `src/data_access/query_engine.py`, make `PandasQueryEngine.aggregate` apply `request.filters` first by reusing `self.query_rows(df, request.filters)` (research.md §1). If the filtered frame is empty, return `[]`. Otherwise group the filtered frame as today. Update the `aggregate` docstring and the module docstring to say the engine receives the **unfiltered** frame and applies the filters itself.
- [X] T011 [US1] In `src/data_access/capabilities.py` `aggregate_rows`, call `_validate_filter_fields(identifier, df, request.filters)` **after** the `group_by` / `value_field` existence checks and **before** the `df.empty` early exit (validation order steps 2 → 3 → 5, research.md §3). Keep the `sum` numeric check on the unfiltered `df`. Set `total_group_count=len(groups)` from the engine result.
- [X] T012 [US1] Run `pytest tests/contract/data_access tests/contract/qa_agent` and `pyright src/`. T006–T008 and every pre-existing test should pass.

**Checkpoint**: US1 is fully functional. Filtered aggregation works and produces the same errors as row queries.

---

## Phase 4: User Story 2 - Use mean, min, max and count_distinct (Priority: P2)

**Goal**: Four new functions. `mean` / `min` / `max` accept only numeric-like fields (classified on the whole source), ignore missing and unparseable values, and return `None` for a group with no usable value. `count_distinct` counts distinct non-missing raw values and accepts any field.

**Independent Test**: Run each new function over `transfers.csv` and compare against the hand-computed values in the fixture section.

### Tests for User Story 2 ⚠️ (write first; they must fail before T017–T019)

- [X] T013 [US2] In `tests/contract/data_access/test_aggregation.py`, add:
  - `test_007_us2_1_mean_min_max_of_simple_values`: group `orgao`, filter `ano equals "2023"`, aggregates mean/min/max of `valor` → MS `mean_valor == 20.0`, `min_valor == 10.0`, `max_valor == 30.0`.
  - `test_007_us2_2_brazilian_formatted_values_parsed_like_sum`: same request → ME `1617.28` / `1234.56` / `2000.0` (`pytest.approx`).
  - `test_007_us2_3_missing_values_ignored_not_zero`: same request → MC mean `5.0` (not `2.5`), min `5.0`, max `5.0`.
  - `test_007_us2_4_all_missing_group_reports_none`: group `orgao`,`uf`, filter `ano equals "2023"`, aggregates mean/min/max/sum of `valor` → for the group `{"orgao": "MC", "uf": "SP"}`, `mean_valor`, `min_valor` and `max_valor` are `None`, and `sum_valor == 0.0` (FR-009, sum unchanged).
- [X] T014 [US2] In the same file, add:
  - `test_007_us2_5_mean_min_max_on_text_field_raise_numeric_type_error`: parametrize over `"mean"`, `"min"`, `"max"` on `fornecedor` → `NumericTypeError`.
  - `test_007_us2_5_numeric_check_uses_whole_source_even_when_filters_match_nothing`: `mean` of `fornecedor` with `ano equals "1999"` → `NumericTypeError`.
  - `test_007_us2_6_count_distinct_excludes_missing`: group `uf`, filter `ano equals "2023"`, `count_distinct` of `fornecedor` → SP `2`.
  - `test_007_us2_7_count_distinct_accepted_on_numeric_and_text_fields`: group `orgao`, `count_distinct` of `mes` → MS `3`, ME `3`, MC `1`, and `count_distinct` of `fornecedor` → MS `2`, ME `2` (Alfa, Gama; r7 missing), MC `2`. Both results are `int`.
- [X] T015 [US2] In the same file, add the edge cases:
  - `test_007_edge_empty_source_returns_zero_groups_for_every_function`: `tmp_path` CSV with header `g,v` and no rows, parametrized over all six functions → `groups == []`, `total_group_count == 0`.
  - `test_007_edge_duplicate_spec_produces_single_key`: two identical `AggregateSpec(value_field="valor", function="mean")` → each group's `results` has exactly one key, `mean_valor`.
  - `test_007_edge_unparseable_values_skipped`: ME `max_valor` for 2023 is `2000.0` and `n/d` doesn't raise.

### Implementation for User Story 2

- [X] T016 [P] [US2] In `src/data_access/models.py`, add `AggregateFunction = Literal["count", "sum", "mean", "min", "max", "count_distinct"]`, set `AggregateSpec.function: AggregateFunction` (with a `Field(description=...)` that lists the six functions, says `sum`/`mean`/`min`/`max` need numeric-like fields, and says the result key is `<function>_<value_field>`), and widen `AggregationGroup.results` to `dict[str, float | int | None]` (data-model.md).
- [X] T017 [US2] In `src/data_access/query_engine.py`, add the module-private `_is_missing(value: object) -> bool`: `True` for `None`, NaN (`pd.isna`), or a `str` that is empty after `strip()` (research.md §4). In `PandasQueryEngine.aggregate`, parse each value field used by `sum`/`mean`/`min`/`max` **once per request**, before grouping. Store it in a temporary column of `float | None` built with `parse_locale_number` (skip `None` inputs, as today). Then compute per group from the table in research.md §5:
  - `count`: `int(len(group))`, unchanged.
  - `sum`: `float` sum of non-null parsed values, `0.0` when there are none (unchanged).
  - `mean` / `min` / `max`: `float` over non-null parsed values, `None` when there are none.
  - `count_distinct`: `int` number of distinct raw values where `not _is_missing(v)`, compared exactly as stored.

  Keep the `f"{spec.function}_{spec.value_field}"` key. Don't let the temporary columns leak into `group_values`, and don't mutate the caller's frame.
- [X] T018 [US2] In `src/data_access/capabilities.py` `aggregate_rows`, after the empty-source exit, raise `NumericTypeError(identifier, spec.value_field)` for every spec whose `function in ("sum", "mean", "min", "max")` and where `not _is_numeric_field(df, spec.value_field)`, using the **unfiltered** `df` (validation step 6, research.md §3). `count` and `count_distinct` get no type check.
- [X] T019 [US2] Run `pytest tests/contract tests/unit` and `pyright src/`. T013–T015 and all earlier tests should pass. Fix any pyright complaints from the widened `results` type in `src/qa_agent` or `src/testset_runner` consumers, if there are any.

**Checkpoint**: US1 and US2 both work on their own. All six functions work with and without filters.

---

## Phase 5: User Story 3 - Order and limit the groups (Priority: P3)

**Goal**: A deterministic default group order, `order_by` over grouping fields and result keys (missing values last in both directions), `limit ≥ 1` applied last, and `total_group_count` / `truncated` reporting.

**Independent Test**: Aggregate a fixture into a known set of groups with `order_by` and `limit`, then check the exact group sequence, `total_group_count` and `truncated`.

### Tests for User Story 3 ⚠️ (write first; they must fail before T024–T027)

- [X] T020 [P] [US3] Create `tests/unit/data_access/test_query_engine.py`, which calls `PandasQueryEngine().aggregate(df, request, numeric_group_fields)` on small in-memory `pd.DataFrame`s of strings. Each test name states one rule:
  - `test_default_order_ascending_by_group_values_missing_last`
  - `test_default_order_independent_of_source_row_order` (the same rows shuffled with `df.sample(frac=1, random_state=...)` give an identical group list)
  - `test_numeric_group_field_sorted_numerically` (`"1","2","10","12"`, not `"1","10","12","2"`)
  - `test_numeric_group_field_unparseable_value_treated_as_missing_and_last`
  - `test_numeric_equal_group_values_tie_broken_by_raw_text` (`"1"` and `"1,0"` come in a fixed order)
  - `test_text_group_field_sorted_by_code_point` (`"Sergipe"` before `"São Paulo"`, uppercase before lowercase)
  - `test_result_key_missing_values_last_ascending`
  - `test_result_key_missing_values_last_descending`
  - `test_later_sort_keys_break_ties_of_earlier_keys`
  - `test_ties_after_all_sort_keys_fall_back_to_default_order`
  - `test_engine_returns_all_groups_no_limit_applied`
- [X] T021 [US3] In `tests/contract/data_access/test_aggregation.py`, add:
  - `test_007_us3_1_order_desc_with_limit_returns_top_n`: `tmp_path` CSV `municipio,valor` with 50 municipalities `M01`…`M50`, one row each, where `valor` for `Mi` is `f"{i}.000,00"` for `i >= 1` (so the value is `i * 1000`). Order `sum_valor desc` with `limit=5` → group values `["M50","M49","M48","M47","M46"]` with sums `50000.0`…`46000.0`, `total_group_count == 50`, `truncated is True`.
  - `test_007_us3_2_order_by_text_grouping_field_ascending`: `transfers.csv` group `uf`, order `uf` → `["MG","RJ","SP"]`.
  - `test_007_us3_2_order_by_numeric_like_grouping_field_numerically`: group `mes`, order `mes` asc → `["1","2","10","12",""]` (values reported as text, the missing `""` last).
  - `test_007_us3_3_multiple_sort_keys_break_ties`: group `orgao`,`uf`, `count_ano`, `order_by=[SortKey(key="count_ano", direction="desc"), SortKey(key="orgao")]` → exactly `[(MS,SP), (ME,MG), (ME,SP), (MS,RJ), (MC,MG), (MC,RJ), (MC,SP)]`.
- [X] T022 [US3] In the same file, add:
  - `test_007_us3_4_missing_sort_values_last_in_both_directions`: group `orgao`,`uf`, filter `ano equals "2023"`, `mean_valor`. Asc → `[(MC,MG), (MS,SP), (MS,RJ), (ME,SP), (ME,MG), (MC,SP)]`. Desc → `[(ME,MG), (ME,SP), (MS,RJ), (MS,SP), (MC,MG), (MC,SP)]`. Also group `mes` ordered `desc` → `["12","10","2","1",""]`.
  - `test_007_us3_5_limit_reports_total_and_truncated`: group `orgao`,`uf`, `count_ano`, `limit=3` → `len(groups) == 3`, `total_group_count == 7`, `truncated is True`.
  - `test_007_us3_6_limit_without_order_uses_default_order`: group `uf`, `limit=2` → `["MG","RJ"]`, `total_group_count == 3`, `truncated is True`.
  - `test_007_edge_limit_larger_than_group_count_not_truncated`: group `uf`, `limit=10` → 3 groups, `truncated is False`.
  - `test_007_us1_filters_plus_limit_limit_counts_groups`: filter `ano equals "2023"`, group `orgao`, order `sum_valor desc`, `limit=1` → only ME `3234.56`, `total_group_count == 3`.
- [X] T023 [US3] In the same file, add:
  - `test_007_us3_7_invalid_sort_key_names_key_and_lists_valid_keys`: group `orgao`, `sum_valor`, `order_by=[SortKey(key="nope")]` → `InvalidSortKeyError` with `.key == "nope"` and `.valid_keys == ["orgao", "sum_valor"]`, whose `str(exc)` contains `'nope'` and `['orgao', 'sum_valor']`.
  - `test_007_us3_7_invalid_sort_key_raised_even_on_empty_source` (`tmp_path` empty CSV).
  - `test_007_us3_8_zero_or_negative_limit_rejected`: parametrize `0`, `-1` → `pydantic.ValidationError` when building `AggregationRequest`.
  - `test_007_sort_key_matching_both_group_field_and_result_key_refers_to_group_field` (`tmp_path` CSV whose column is literally named `sum_valor`; research.md §6).

### Implementation for User Story 3

- [X] T024 [P] [US3] In `src/data_access/exceptions.py`, add `class InvalidSortKeyError(DataAccessError)`. `__init__(self, identifier: str, key: str, valid_keys: list[str])` stores all three and builds the message `f"Sort key {key!r} is not valid for data source {identifier!r}; valid keys: {valid_keys!r}"`, which gives exactly `Sort key 'x' is not valid for data source 'id'; valid keys: ['uf', 'sum_valor']` (data-model.md).
- [X] T025 [P] [US3] In `src/data_access/models.py`, add `class SortKey(BaseModel)` with `key: str` and `direction: Literal["asc", "desc"] = "asc"`, each with a `Field(description=...)`. The `key` description says it must be a `group_by` field or a result key `<function>_<value_field>`. Add to `AggregationRequest`:
  - `order_by: list[SortKey] = Field(default_factory=list, description=...)`: applied in list order, later keys break ties, missing values go last, and the default order is ascending by grouping values.
  - `limit: int | None = Field(default=None, ge=1, description=...)`: the maximum number of **groups**, applied after ordering.
- [X] T026 [US3] In `src/data_access/query_engine.py`, change the signature of `QueryEngine.aggregate` and `PandasQueryEngine.aggregate` to `aggregate(self, df, request, numeric_group_fields: frozenset[str]) -> list[AggregationGroup]` (data-model.md "QueryEngine protocol"). After computing the groups (built with `groupby(..., dropna=False, sort=False)` as today), order them in plain Python (research.md §7):
  1. **Base pass**: stable-sort by the `group_by` fields in order, ascending. A numeric-like field (in `numeric_group_fields`) compares by `parse_locale_number(raw)`, and a text field compares by plain `str` (code point, no locale or casefold). Missing (`_is_missing`) or unparseable values go last. The final tie-breaker is the tuple of raw group-value strings.
  2. **Sort-key passes**, from the last `order_by` key to the first. Split into present and missing values, stable-sort the present ones with `reverse=(direction == "desc")`, and append the missing ones. A key found in `request.group_by` is a grouping field and wins over a result key of the same name. Otherwise it is a result key, compared numerically, with `None` as missing.

  Don't apply the limit here. Update the method docstring with the filter → group → aggregate → order pipeline.
- [X] T027 [US3] In `src/data_access/capabilities.py` `aggregate_rows`, implement validation step 4 (research.md §3), after the filter validation and before the empty-source exit. Build `valid_keys` as the `group_by` fields, then `f"{s.function}_{s.value_field}"` for each spec, in request order and without duplicates. Raise `InvalidSortKeyError(identifier, key, valid_keys)` for the first `order_by` key not in it. After step 6, compute `numeric_group_fields = frozenset(f for f in request.group_by if _is_numeric_field(df, f))` on the unfiltered `df` and call `_ENGINE.aggregate(df, request, numeric_group_fields)`. Then set `total_group_count = len(all_groups)`, `groups = all_groups[: request.limit]` when `limit` is set, and `truncated = total_group_count > len(groups)`. Update the `aggregate_rows` docstring with the pipeline and the error order from contracts/aggregation.md.
- [X] T028 [US3] Run `pytest tests/contract tests/unit` and `pyright src/`. T020–T023 and all earlier tests should pass. If a pre-existing test relied on first-appearance group order, change only its ordering expectation and note it in the commit message (FR-016 allows only the order to change).

**Checkpoint**: All three stories work together and each one works on its own.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Agent-facing documentation (FR-017), documentation deliverables (Principle III) and evidence (SC-003, SC-004).

- [X] T029 [P] Create `tests/unit/qa_agent/test_tools_description.py`. Build the agent with `build_agent(AgentSettings(model_name="test", instrument=False))` from `src/qa_agent/agent_factory.py`. Get the registered `aggregate_rows` `ToolDefinition` by running it with a `FunctionModel` whose function records `info.function_tools` on its first call and then returns the final output, following the `FunctionModel` pattern in `tests/contract/qa_agent/test_answer_question_dispatch.py`. Assert that:
  - the description mentions that filters apply before grouping/aggregation, names all six functions (`count`, `sum`, `mean`, `min`, `max`, `count_distinct`), and contains the `<function>_<value_field>` naming (for example `sum_valor`) plus `order_by`, `desc` and `limit`,
  - the `parameters_json_schema` for `request` includes `filters`, `order_by`, `limit` and the six-value `function` enum (contracts/aggregate-rows-tool.md "Tests").
- [X] T030 Add a Google-style docstring to `aggregate_rows` in `src/qa_agent/tools.py`, with an `Args:` section for `identifier` and `request`. It must cover every bullet in contracts/aggregate-rows-tool.md "Tool description": purpose; filters apply first (same conditions as `query_rows`, combined with AND); the six functions and their numeric/any-field rules (`null` when a group has no usable value); the result-key convention `<function>_<value_field>` accepted by `order_by`; `order_by` `{key, direction}` with `asc` as the default, `desc` + `limit` for top N, missing values last, and the default ascending order by grouping values; a grouping field wins a name clash with a result key; the limit is ≥ 1 and counts groups; the result reports `total_group_count` and `truncated`. Don't change the wrapper's code, and don't edit `prompts/system_v1.md` (research.md §9). T029 should then pass.
- [X] T031 [P] Check that the module docstrings in `src/data_access/query_engine.py` and `src/data_access/capabilities.py` describe the new engine/capability split: the engine does filter → group → aggregate → order, and the capability does validation, numeric classification on the unfiltered source, and the limit and counts (research.md §1). Also mark `specs/001-data-access-tools/contracts/aggregation.md` as superseded by `specs/007-aggregate-rows-enhancements/contracts/aggregation.md` with a one-line note at its top.
- [X] T032 Run the full CI gate from quickstart.md §1: `pytest tests/contract tests/unit -v` and `pyright src/`. Everything must pass.
- [X] T033 Run the direct capability check from quickstart.md §2 against `data/datasets/orcamentos-aeb-csv`. Make one request that combines a year filter, `sum` + `mean` + `count_distinct`, `order_by` sum `desc` and `limit=3`, and check that the sums don't increase, `total_group_count`/`truncated` are correct, and the top sum matches a hand-summed `query_rows` over the same filter. Also confirm the three documented errors (`InvalidSortKeyError`, `NumericTypeError`, `pydantic.ValidationError`). Record the commands and outputs in `specs/007-aggregate-rows-enhancements/results.md` under "Direct capability check".
- [ ] T034 Run the agent end-to-end check from quickstart.md §3 (SC-003): `python -m web_ui.cli`, then ask "Quais foram as 3 ações com maior valor orçado em 2023?". Confirm in `data/logs/qa_agent_runs.jsonl` that the answer used **one** `aggregate_rows` call with `filters`, `order_by` `desc` and `limit`, and no `query_rows` call followed by the agent's own arithmetic. Record it in `results.md` under "Agent end-to-end".
- [ ] T035 Run the post-feature testset from quickstart.md §4 with the same settings as the T002 baseline, then `python -m testset_runner.cli compare <baseline> <feature>`. In `specs/007-aggregate-rows-enhancements/results.md`, record the run files, the overall and per-category match rates, the match outcome for each aggregation-dependent question id from T002, and the hand count from the retrieval traces of answers whose numbers appear in no tool result, for both runs (SC-004, research.md §10). State whether SC-004 holds.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies. T001 blocks every contract test. T002 can run at any time before T035, but must run against commit `6636991`.
- **Foundational (Phase 2)**: Depends on T001 (T005 uses the fixture). It blocks all user stories.
- **US1 (Phase 3)**: Depends on Phase 2.
- **US2 (Phase 4)**: Depends on Phase 2. Several of its tests use `filters` (only to scope data), so in practice it follows US1, or you can drop the filters from those tests if you implement it alone.
- **US3 (Phase 5)**: Depends on Phase 2. Tests T022 (US3.4, filters+limit) use `filters` and `mean`, so it runs after US1 and US2 in practice. The engine and capability work (T026–T027) touches the same functions as T010/T011/T017/T018, so do it after them.
- **Polish (Phase 6)**: T029/T030 depend on T009, T016 and T025 (the schema fields exist). T032–T035 depend on everything else.

### User Story Dependencies

- **US1 (P1)**: Needs only the foundation. It's the MVP.
- **US2 (P2)**: Independent of US1 in logic. It shares `models.py`, `query_engine.py`, `capabilities.py` and the contract test file, so implement it after US1 to avoid edit conflicts.
- **US3 (P3)**: Independent in logic. Same shared files, so it comes after US2.

### Within Each User Story

- Contract tests are written first, in the single shared file `tests/contract/data_access/test_aggregation.py` (sequential, not [P]), and must fail before implementation.
- Models → engine → capability → run the tests.

### Parallel Opportunities

- T002 (baseline testset run) runs in parallel with all code work.
- US2: T016 (`models.py`) can run in parallel with the tests T013–T015 (a different file).
- US3: T020 (new unit-test file), T024 (`exceptions.py`) and T025 (`models.py`) can all run in parallel with each other and with T021–T023.
- Polish: T029 (new test file) and T031 (docstrings / 001 note) can run in parallel. T030 follows T029.

---

## Parallel Example: User Story 3

```bash
# Different files, no mutual dependencies — launch together:
Task: "T020 [US3] Create tests/unit/data_access/test_query_engine.py (ordering rules)"
Task: "T024 [US3] Add InvalidSortKeyError to src/data_access/exceptions.py"
Task: "T025 [US3] Add SortKey, order_by, limit to src/data_access/models.py"
# Meanwhile, sequentially in tests/contract/data_access/test_aggregation.py:
Task: "T021 → T022 → T023"
# Then:
Task: "T026 engine ordering" → "T027 capability validation + limit" → "T028 run gate"
```

## Parallel Example: User Story 2

```bash
Task: "T016 [US2] AggregateFunction + widened results in src/data_access/models.py"
Task: "T013 → T014 → T015 contract tests in tests/contract/data_access/test_aggregation.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: the fixture (T001), with the baseline run (T002) started in parallel.
2. Phase 2: the result-shape fields and the `_is_numeric_field` helper.
3. Phase 3: filters. **Stop and validate**: T012 passes, and scoped questions ("in 2023") can now be answered with one aggregation call.

### Incremental Delivery

1. Setup + Foundational → the result shape is ready.
2. US1 (filters) → test → commit (MVP).
3. US2 (mean/min/max/count_distinct) → test → commit.
4. US3 (order/limit + deterministic default order) → test → commit.
5. Polish: tool description (FR-017), docs, then the evidence runs (T033–T035) in `results.md`.

Each commit keeps `pytest tests/contract tests/unit` and `pyright src/` green.

---

## Notes

- [P] = different files, no dependency on incomplete tasks.
- All contract tests live in one file, so they're sequential within a story.
- Expected values are the hand-computed literals in the "Shared test fixture" section. Don't compute them in the test with pandas.
- `data_access` must not import `pydantic-ai` (FR-019).
- `sum` keeps returning `0.0` for a group with no usable values. Only `mean`/`min`/`max` return `None`.
