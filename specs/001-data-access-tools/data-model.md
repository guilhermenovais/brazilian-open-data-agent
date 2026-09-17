# Phase 1 Data Model: Data Access Tool Layer

All I/O-crossing shapes are pydantic v2 `BaseModel`s (Constitution Engineering Principle 5).
Internal-only helper types (the `Dataset` abstraction, reader/engine protocols) are plain
Python and are documented here for completeness but are not part of the external contract.

## Entities

### DataSourceInfo *(discovery output — one per source)*

| Field        | Type                     | Notes |
|--------------|--------------------------|-------|
| `identifier` | `str`                    | Stable, relative-path-based (e.g. `"reports/2024/sales.csv"`); POSIX separators regardless of host OS. Never an absolute path. |
| `format`     | `Literal["csv", "json"]` | Derived from file extension. |
| `readable`   | `bool`                   | `False` when the source failed to parse (FR-001a); `True` otherwise. |

Validation: `identifier` non-empty; must be unique within a `DiscoveryResult` (enforced by
`Dataset`, not by the model itself — see Collision Handling below).

### DiscoveryResult

| Field     | Type                   | Notes |
|-----------|------------------------|-------|
| `sources` | `list[DataSourceInfo]` | May be empty (Acceptance Scenario US1.3). |

### FieldInfo *(schema inspection output — one per observed field)*

| Field  | Type                          | Notes |
|--------|-------------------------------|-------|
| `name` | `str`                         | Field/column name as observed in the source. |
| `type` | `Literal["numeric_like", "text"]` | Computed from the sample per research.md §4 (≥80% of non-null sampled values parse numerically). |

### SchemaInspectionResult

| Field        | Type                        | Notes |
|--------------|-----------------------------|-------|
| `identifier` | `str`                       | Echoes the requested source. |
| `fields`     | `list[FieldInfo]`           | Union of fields observed across the sample (JSON sources may have heterogeneous records — US2 Acceptance Scenario 2). |
| `sample`     | `list[dict[str, str \| None]]` | ≤ `SAMPLE_SIZE_CAP` (20) records; values are raw strings as found in the source (or `None` if the field is absent from that record); never re-formatted or numerically coerced. |

### FilterCondition *(row query input — discriminated union on `op`)*

| Variant            | Fields                                             | Semantics |
|--------------------|-----------------------------------------------------|-----------|
| `EqualsCondition`   | `field: str`, `op: Literal["equals"]`, `value: str`  | Exact string match on the field's raw value. |
| `ContainsCondition` | `field: str`, `op: Literal["contains"]`, `value: str`| Case-insensitive substring match on the field's raw value. |
| `RangeCondition`    | `field: str`, `op: Literal["range"]`, `min: float \| None`, `max: float \| None` | Matches rows whose field's normalized numeric value (research.md §3) is ≥ `min` (if given) and ≤ `max` (if given). Requires the field be `numeric_like`; at least one of `min`/`max` must be set. |

Multiple `FilterCondition`s in one request combine with logical AND (FR-005).

### RowQueryResult

| Field               | Type                | Notes |
|---------------------|---------------------|-------|
| `identifier`        | `str`               | Echoes the requested source. |
| `rows`               | `list[dict[str, str \| None]]` | ≤ `ROW_QUERY_CAP` (100) rows; raw string values, unmodified. |
| `returned_count`     | `int`               | `len(rows)`. |
| `total_match_count`  | `int`               | Exact count of rows matching all filters, computed in-memory (dataset fits in memory per spec Assumptions). |
| `truncated`          | `bool`              | `True` iff `total_match_count > returned_count` (FR-011). |

### AggregateSpec *(aggregation input — one per requested aggregate)*

| Field         | Type                        | Notes |
|---------------|-----------------------------|-------|
| `value_field` | `str`                       | Field the aggregate is computed over. |
| `function`    | `Literal["count", "sum"]`   | `count` counts rows in the group (any field type); `sum` requires the field be `numeric_like` (FR-013). |

### AggregationRequest

| Field         | Type                   | Notes |
|---------------|------------------------|-------|
| `group_by`    | `list[str]`            | One or more fields; non-empty. |
| `aggregates`  | `list[AggregateSpec]`  | Non-empty. |

### AggregationGroup

| Field          | Type                        | Notes |
|----------------|-----------------------------|-------|
| `group_values` | `dict[str, str \| None]`     | The `group_by` field values identifying this group. |
| `results`      | `dict[str, float \| int]`    | Keyed as `f"{function}_{value_field}"` (e.g. `"sum_price"`, `"count_id"`); `count` yields `int`, `sum` yields `float`. |

### AggregationResult

| Field        | Type                     | Notes |
|--------------|--------------------------|-------|
| `identifier` | `str`                    | Echoes the requested source. |
| `groups`     | `list[AggregationGroup]` | May be empty when the source has no rows (US4 Acceptance Scenario 5). Broken out by the full combination of `group_by` values (FR-008). |

## Errors (raised, not returned — see research.md §9)

| Exception                   | Raised when | Carries |
|------------------------------|-------------|---------|
| `DataSourceNotFoundError`    | `identifier` not present in the dataset (FR-012). | `identifier` |
| `UnreadableSourceError`      | Inspection/query/aggregation targets a source flagged unreadable at discovery (FR-001a). | `identifier`, parse error detail |
| `FieldNotFoundError`         | A filter field, group-by field, or aggregate value field doesn't exist in the source (FR-012). | `identifier`, `field` |
| `NumericTypeError`           | A `range` filter or `sum` aggregate targets a field that isn't `numeric_like` (FR-013). | `identifier`, `field` |
| `IdentifierCollisionError`   | Two or more physical sources resolve to the same identifier (FR-012a). | `identifier`, list of colliding physical paths |

## Internal (non-contract) types

### `Dataset` (internal abstraction)

Constructed from a root folder path. Walks the folder tree (including subfolders), keeping
an internal tree/index of physical files, but exposes only:

- `list_sources() -> list[DataSourceInfo]` — flat list; raises `IdentifierCollisionError` if
  two physical files would resolve to the same relative-path identifier (e.g.
  case-insensitive filesystem collision, or a future multi-root merge).
- `resolve(identifier: str) -> Path` — internal use only, translates an identifier back to
  its physical location for a reader to open; never exposed outside `Dataset`/readers
  (FR-001b: capabilities never see absolute/physical paths).

Non-data files (e.g. `README.md`) are excluded from `list_sources()` based on recognized
extension (`.csv`, `.json`) (US1 Acceptance Scenario 2).

### `DataSourceReader` (Protocol)

```
class DataSourceReader(Protocol):
    def read(self, path: Path) -> pandas.DataFrame: ...
```

Implementations: `CsvReader`, `JsonReader` (research.md §7). Always returns string-typed
columns (research.md §2). Raises a parse error internally, caught by `Dataset` and turned
into `readable=False` at discovery time, or re-raised as `UnreadableSourceError` when a
later capability targets that source (FR-001a).

### `QueryEngine` (Protocol)

```
class QueryEngine(Protocol):
    def query_rows(self, df: pandas.DataFrame, filters: list[FilterCondition]) -> pandas.DataFrame: ...
    def aggregate(self, df: pandas.DataFrame, request: AggregationRequest) -> list[AggregationGroup]: ...
```

Implementation: `PandasQueryEngine` (research.md §6).

## Relationships

```
Dataset 1---* DataSourceInfo (via list_sources())
Dataset 1---1 DataSourceReader (selected per source by format)
DataSourceReader ---> pandas.DataFrame (raw-string columns) ---> QueryEngine
FilterCondition *---1 RowQueryResult (AND-combined)
AggregateSpec *---1 AggregationRequest ---> AggregationResult 1---* AggregationGroup
```
