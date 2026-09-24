# Research: Richer Aggregation (Filters, Functions, Ordering, Limit)

**Feature**: `007-aggregate-rows-enhancements` | **Date**: 2026-09-24

The Technical Context had no open `NEEDS CLARIFICATION` items: the stack, the engine and the
error-handling path all exist. The decisions below settle *where* each new behavior lives and
the exact semantics the spec leaves to the design. Each one was checked against the current
code (`src/data_access/*`, `src/qa_agent/tools.py`) and the installed `pydantic-ai` 2.45.0.

---

## §1 Which layer does what

**Decision**: Keep the existing split and extend it.

| Step | Layer | Why |
|------|-------|-----|
| Field existence, numeric-type checks, sort-key validity | `capabilities.aggregate_rows` | Existing rule: validation that needs the identifier for error messages lives in `capabilities.py` (`query_engine.py` module docstring). |
| Numeric-like classification of fields | `capabilities.aggregate_rows` | It must look at the **whole, unfiltered** source (Clarification 3), and the capability is the only place that has it before filtering. |
| Filter → group → aggregate → order | `PandasQueryEngine.aggregate` | Purely mechanical. A future `DuckDBQueryEngine` would push these into `WHERE` / `GROUP BY` / `ORDER BY`. |
| Limit, `total_group_count`, `truncated` | `capabilities.aggregate_rows` | Same as `query_rows`: the engine returns every match, and the capability applies the cap and reports the counts. |

`QueryEngine.aggregate` gains one parameter, `numeric_group_fields: frozenset[str]`: the
grouping fields that the capability classified as numeric-like. The engine needs it to order
grouping values (FR-010), but it can't classify on its own because classification must use
the unfiltered source.

**Alternatives considered**:
- *Capability filters first (`_ENGINE.query_rows`), then passes the filtered frame to
  `aggregate`.* Works for pandas, but it splits one logical query across two engine calls, so
  a SQL engine could not run it as a single statement. Rejected. The engine still reuses its
  own `query_rows` internally, so filter semantics can't drift (FR-001).
- *Engine classifies fields itself from the frame it receives.* It would need the unfiltered
  frame and would duplicate `is_numeric_like` sampling policy inside the engine. Rejected.
- *Engine applies the limit.* That would make the engine report two numbers, which `query_rows`
  doesn't do. Rejected for consistency.

---

## §2 Numeric-like classification: one rule, reused everywhere

**Decision**: Add a private helper `_is_numeric_field(df, field)` in `capabilities.py` that
returns `is_numeric_like(df[field].head(SAMPLE_SIZE_CAP).tolist())`. This is the exact rule
that `inspect_schema`, `_validate_filter_fields` and today's `sum` check already use. It is
applied to the **unfiltered** frame for:
- range filters (through the existing `_validate_filter_fields`, unchanged),
- `sum` / `mean` / `min` / `max` value fields,
- grouping fields, to decide numeric vs text ordering.

**Rationale**: Clarification 3 and FR-006 require the same classification that schema
inspection reports. Today that rule is copied inline in two places, and this feature would add
two more. One helper removes the copies without changing the rule.

**Alternatives considered**: Classifying on all rows instead of the first 20. This would
disagree with what `inspect_schema` tells the agent, so the agent could see a field reported
as `text` and then get a different verdict. Rejected. Changing the sampling policy is a
separate decision.

---

## §3 Validation order and the empty-source case

**Decision**: `aggregate_rows` validates in this order:

1. `dataset.read(identifier)`, which raises `DataSourceNotFoundError` / `UnreadableSourceError` (unchanged).
2. Every `group_by` field and `value_field` exists, else `FieldNotFoundError` (unchanged).
3. Filters, through the existing `_validate_filter_fields`: existence, then range → numeric-like.
4. Every sort key refers to a grouping field or a requested result key, else `InvalidSortKeyError` (§6).
5. **If the source has no rows, return zero groups** (unchanged early exit).
6. `sum` / `mean` / `min` / `max` value fields are numeric-like, else `NumericTypeError`.

**Rationale**:
- Steps 3–4 come before the empty-source exit so that filters are validated *exactly* like
  `query_rows` validates them (FR-003). `query_rows` on an empty source with a range filter
  raises `NumericTypeError` today, and aggregation now does the same. Sort-key validity
  depends only on the request, so it is also checked regardless of the data.
- Step 5 stays before step 6. That keeps the spec's edge case ("an empty source returns zero
  groups for every function") and today's behavior, where `sum` over an empty source returns
  `[]` (`test_us4_5`).
- Step 6 runs on the unfiltered frame, so a filter that matches nothing still gets the
  not-numeric error (FR-004, spec edge case "Filters that match nothing, plus an invalid
  function").

---

## §4 Missing values

**Decision**: A value is **missing** when it is `None`/NaN (JSON sources, pandas group keys)
or a string that is empty after `strip()` (CSV sources are read with `na_filter=False`, so an
empty cell arrives as `""`). The engine has one module-private `_is_missing(value)` predicate,
used by `count_distinct` and ordering. Numeric functions don't need it:
`parse_locale_number` already returns `None` for empty and unparseable strings.

Group values are **reported** exactly as today (`None` for a NaN key, otherwise `str(value)`,
so a CSV `""` stays `""`). Only ordering treats `""` as missing.

**Rationale**: Scenario US2.6 ("A", "B", "A" and one missing value → 2) must hold for CSV
sources, where the "missing value" is `""`. Changing how group values are reported would
violate FR-016.

---

## §5 Aggregate function semantics (pandas)

**Decision**: Parse each numeric value field **once per request**, before grouping. Add a
column of `float | None` produced by `parse_locale_number`, then compute per group:

| Function | Per-group value | Empty / no usable values |
|----------|-----------------|--------------------------|
| `count` | `len(group)`, all rows, missing included (unchanged) | n/a (a group has ≥ 1 row) |
| `sum` | sum of parsed non-null values (unchanged) | `0.0` (unchanged, FR-009) |
| `mean` | arithmetic mean of parsed non-null values | `None` |
| `min` / `max` | min / max of parsed non-null values | `None` |
| `count_distinct` | number of distinct raw values that aren't missing (§4), compared exactly as stored | `0` |

Types: `count` and `count_distinct` return `int`, and the others return `float` (or `None`).
The existing `<function>_<field>` key naming is kept, and a request that repeats the same
function and field produces one key (a dict write, as today).

**Rationale**: Parsing once instead of once per group keeps the cost linear in rows. The
current implementation re-parses inside each group, and that pattern would be repeated for
three more functions. `sum` keeps returning `0.0` for a group whose values are all missing,
because FR-009 forbids changing its meaning. Only the new functions use `None`.

**Alternatives considered**: `groupby().agg({...})` with named aggregations. This is faster
on large frames, but it needs custom lambdas for locale parsing and `None`-on-empty anyway.
Datasets here are small open-data CSVs, and the per-group loop already exists and is tested.
Rejected as speculative optimization (Principle VII).

---

## §6 Sort keys: shape, validation, and name clashes

**Decision**:
- `SortKey(key: str, direction: Literal["asc", "desc"] = "asc")`.
- Valid keys are the `group_by` fields plus the result keys of the requested aggregates. An
  unknown key raises the new `InvalidSortKeyError(identifier, key, valid_keys)`, a
  `DataAccessError`, so `qa_agent.tools` already turns it into `ModelRetry` (FR-018). The
  message names the key and lists the valid choices in request order (FR-012, SC-005).
- If a name is both a grouping field and a result key (for example, a source column literally
  called `sum_valor`), the sort key refers to the **grouping field**. This is documented in the
  tool description. It is rare enough that rejecting the request isn't worth an extra rule.

**Alternatives considered**: Checking sort keys in a pydantic `model_validator` on
`AggregationRequest`. It's possible, because the check depends only on the request. But the
error would arrive as a pydantic `ValidationError` instead of a typed `DataAccessError`, so
the error family would be inconsistent with the other data-access errors, and direct callers
(the test harness) couldn't `pytest.raises` a specific type. Rejected.

---

## §7 Ordering algorithm

**Decision**: Order the list of computed groups in plain Python with **stable multi-pass
sorting**:

1. **Base pass: default order** (FR-011). Sort by all grouping fields in `group_by` order,
   ascending, missing values last. As a final tie-breaker, compare the raw grouping-value
   strings, so that numeric-equal but textually different values (`"1"` vs `"1,0"`) still get a
   fixed order. The result is fully determined by the group values and never by source row
   order.
2. **Sort-key passes**, from the *last* sort key to the first. Each pass partitions the groups
   into *present* and *missing*, stable-sorts the present ones by value with
   `reverse=(direction == "desc")`, and appends the missing ones after them. Python's
   `list.sort` stays stable when `reverse=True`, so ties keep the order from the earlier
   passes.

Value comparison:
- **Result keys**: numeric. `None` is missing.
- **Numeric-like grouping fields** (from `numeric_group_fields`): `parse_locale_number` of the
  raw value. Values that are missing or can't be parsed count as missing (spec edge case).
- **Text grouping fields**: plain Python `str` ordering (Unicode code points), with no locale
  collation and no case folding.

**Rationale**: With the multi-pass approach, "missing last in both directions" is trivial,
whereas a single composite key would need direction-aware sentinels. Code-point ordering
doesn't depend on the host's `LC_COLLATE`, so results are the same on every machine
(Principle I). A consequence is that `"São Paulo"` sorts after `"Sergipe"`. This is
acceptable because text ordering of grouping values is a presentation convenience. Answers
that depend on order ("top N by value") sort on numeric results.

**Alternatives considered**: `DataFrame.sort_values(..., na_position="last", key=...)`. That
means building a results frame and per-column key callables, and mixed numeric/text keys get
awkward. The group list is small (≤ number of distinct combinations), so Python sorting is
simpler. Rejected. `locale.strxfrm`: machine-dependent. Rejected (Principle I).

---

## §8 Limit and result shape

**Decision**:
- `AggregationRequest.limit: int | None = Field(default=None, ge=1)`. When the limit is `0`
  or negative, pydantic rejects the request. At the tool boundary, pydantic-ai sends that
  validation error back to the model as a retry prompt (it counts against the tool's
  `retries=10`, not the step budget), so it is correctable (FR-013, FR-018). This works the
  same way as the existing `group_by` `min_length=1` constraint.
- `AggregationResult` gains two **required** fields: `total_group_count: int` (groups after
  filtering, before the limit) and `truncated: bool` (`total_group_count > len(groups)`).
  These are the names `RowQueryResult` uses for the same idea (`total_match_count`,
  `truncated`), adapted to groups.
- `AggregationGroup.results` widens to `dict[str, float | int | None]`.

**Rationale**: Aggregation results are never persisted as models. `RetrievalStep` stores only
a `result_summary` string. So the new required fields don't break any stored data, and
keeping them required means no code path can forget to set them. No default limit (spec
Assumptions).

---

## §9 How the agent learns about the new parameters (FR-017)

**Decision**: pydantic-ai 2.45.0 builds a tool's description from the function docstring, and
its parameter descriptions from the docstring's `Args:` section (checked with a probe in the
project venv). Nested model fields take their descriptions from `Field(description=...)`.
Therefore:
- `qa_agent.tools.aggregate_rows` gets a docstring. It says that filters apply before grouping,
  lists the six functions and their numeric/any-field rules, gives the `<function>_<field>`
  result-key convention used by `order_by`, describes the default order, the missing-last
  rule and the limit, and says that the result reports `total_group_count` / `truncated`.
- The new request fields (`filters`, `order_by`, `limit`) and `SortKey` fields get short
  `Field(description=...)` texts in `data_access/models.py`.
- The system prompt (`prompts/system_v1.md`) is **not** changed. It already tells the agent to
  use the aggregation tool, and Engineering Principle 8 forbids editing a versioned prompt in
  place without evidence that it needs to change.

**Rationale**: The tool description travels with the tool schema, so every run that uses the
new tool gets its documentation. The docstring is the only description channel pydantic-ai
reads from an undecorated function.

**Note**: None of the four tools has a docstring today. This feature documents only
`aggregate_rows` (scope). The other three are unchanged.

---

## §10 Evidence and evaluation (SC-004, Principles I–II)

**Decision**: SC-004 is checked with the existing testset runner. Record a baseline run on
`data/testsets/orcamentos-aeb-csv.json` at the pre-feature commit and a run after the change
with the same `TargetConfiguration` and `RetryPolicy`, then compare them with
`python -m testset_runner.cli compare` (see quickstart.md). The comparison reports the match
rate on the whole testset and per question `category` (`by_category`). The questions that need
filtered / mean / extreme / distinct / top-N aggregation are identified in the results note by
question id, because the testset's categories don't map one-to-one onto these needs. The tool-trace side of SC-004 ("the agent doesn't do more of
its own arithmetic") is read from `RetrievalStep`s in both runs, by counting answers whose
cited numbers appear in no tool result. That check is done by hand and kept in the results
note, not automated in this feature.

**Rationale**: The feature is motivated by the spec's documented gap (questions that need
scoped/averaged/top-N aggregates can't be answered in one mechanical call, which violates
Principle VI). The before/after runs are the reproducible evidence of its effect.
