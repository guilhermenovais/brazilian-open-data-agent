# Phase 0 Research: Data Access Tool Layer

## 1. Scope boundary: plain tool layer vs. pydantic-ai wiring

**Decision**: This feature implements only the plain, framework-agnostic Python capabilities
(discovery, inspection, query, aggregation) and their pydantic I/O models and typed
exceptions. It does **not** implement `@agent.tool` adapters, `RunContext[Deps]` wiring, or
prompt/briefing content.

**Rationale**: Constitution Engineering Principle 1 requires orchestration (`Agent`, tool
registration, `RunContext`, prompt assembly) to stay in a thin integration layer separate
from business logic. The spec's four capabilities are pure business logic with no mention of
prompts, agent loops, or model configuration. Keeping the pydantic-ai adapter layer out of
this feature's scope lets the capabilities be unit-tested without a model in the loop
(Engineering Principle 6) and keeps this plan focused on what the spec actually requires.

**Alternatives considered**: Building the `@agent.tool` wrappers in the same feature was
rejected — it would conflate two independently testable layers and isn't required by any
FR/SC in the spec.

## 2. Numeric parsing must never be delegated to the file-format parser

**Decision**: CSV and JSON values are read as raw strings only — never auto-coerced to
`int`/`float` by the parser (e.g. `pandas.read_csv(..., dtype=str)`, `json.load` followed by
explicit string coercion of scalar leaf values). All numeric interpretation happens in a
single dedicated normalization function applied per value, never per field.

**Rationale**: FR-003 requires the content sample to show values "as found in the source"
(e.g. `"1.234,56"` unchanged). FR-009/FR-010 require per-value locale detection. If the
parser auto-infers numeric types (pandas' default CSV behavior, or JSON's native number
type), the original formatting is destroyed before normalization ever runs, and a value like
`"1.234,56"` would either fail to parse as a number at all or be silently misread. Reading
everything as strings first is the only way to preserve both the original display value and
give the normalizer a faithful input.

**Alternatives considered**: Letting pandas infer dtypes and re-formatting for display was
rejected — irreversible information loss (e.g. distinguishing `"1.234,56"` from `"1,234.56"`
after pandas has already parsed both as floats is not generally possible).

## 3. Per-value locale detection algorithm

**Decision**: A single deterministic function `parse_locale_number(raw: str) -> float | None`
implements:

1. Strip surrounding whitespace. Empty string → `None` (unparseable).
2. All-digits (optional leading `-`), no separators → parse directly as an integer. Unambiguous.
3. Contains both `,` and `.`: the **rightmost** separator is the decimal point; the other
   character must occur only as a grouping separator with exactly 3 digits between every
   occurrence (standard grouping rule). If grouping is inconsistent → unparseable.
   - `"1.234,56"` → decimal `,`, grouping `.` → `1234.56`
   - `"1,234.56"` → decimal `.`, grouping `,` → `1234.56`
4. Contains only one kind of separator (`,` or `.`), possibly repeated:
   - If the last group after the final separator has 1–2 digits → that separator is the
     decimal point (e.g. `"1234,56"` → `1234.56`, `"1234.5"` → `1234.5`).
   - If the last group after the final separator has exactly 3 digits and every other group
     is also 3 digits → treated as a grouping separator on an integer (e.g. `"1,234"` →
     `1234`, `"1.234"` → `1234`).
   - Anything else (inconsistent grouping, 4+ trailing digits, etc.) → unparseable.
5. Anything not matching the above → unparseable (`None`).

This is applied independently to every value; there is no per-field or per-source locale
setting.

**Rationale**: Directly implements FR-009/FR-010/the clarification "detect the locale
convention per individual value." Rule 4's 1–2-vs-3-trailing-digit heuristic is the same
disambiguation rule used by common locale-aware parsers and matches real-world Brazilian
(`,` decimal, always 2 digits for currency-like values) and US (`.` decimal) formatting
conventions.

**Alternatives considered**: A per-field "detect the dominant convention, apply to all
values" strategy was rejected outright — it directly contradicts the resolved clarification
that mixed-convention values within one field must each be normalized independently.

## 4. Numeric-like field classification threshold

**Decision**: A field is classified `numeric_like` when ≥ 80% of its **non-null sampled**
values parse successfully via `parse_locale_number`. Below that threshold, the field is
`text`, and FR-013's error applies to any numeric operation against it.

**Rationale**: FR-013a requires a "strong majority" threshold without pinning a number; 80%
is a defensible strong-majority cutoff that tolerates a small amount of genuine data mess
(stray blanks, a few malformed entries) without misclassifying an actually-numeric field.
Classification is computed from the same bounded sample used for inspection (per the Field
entity definition in the spec), not a full-file scan — consistent with SC-002's requirement
that inspection needs no separate full scan.

**Alternatives considered**: 100% (any non-numeric value disqualifies the field) was
rejected — it would misclassify realistic numeric fields containing a handful of "N/A"
entries, which the spec explicitly wants tolerated (FR-013a). A lower threshold like 50% was
rejected as not matching "strong majority."

## 5. Default bounded caps

**Decision**: `SAMPLE_SIZE_CAP = 20` records for schema inspection; `ROW_QUERY_CAP = 100`
rows for filtered row query results. Both are fixed module-level constants, not
caller-configurable, per the spec's Assumptions.

**Rationale**: FR-011/SC-006 require a fixed, predictable bound; the spec explicitly defers
the exact number to implementation ("fixed, reasonable default cap"). 20 records is enough to
observe real field-value variety (including rare formatting variants) without returning a
large payload; 100 rows keeps row-query responses small while still being useful for
fact-finding queries.

**Alternatives considered**: Making caps configurable per call was rejected — spec
Assumptions explicitly place this out of scope for the initial contract.

## 6. Query engine backend

**Decision**: Define a `QueryEngine` `Protocol` with `query_rows` and `aggregate` methods;
implement it with a `PandasQueryEngine` backed by an in-memory `pandas.DataFrame` of raw
string values (see §2).

**Rationale**: Constitution Engineering Principle 2 names this exact interface
(`QueryEngine` protocol, `PandasQueryEngine` today, room for a `DuckDBQueryEngine` later) as
a required pattern for this codebase. Using pandas for filtering/grouping over in-memory data
that's guaranteed to fit in memory (spec Assumptions) is a natural fit and avoids hand-rolling
row iteration.

**Alternatives considered**: Plain-Python list-of-dicts iteration without pandas was
rejected — it would need to be re-implemented once a second backend is introduced, violating
Engineering Principle 2's "trying a new approach must mean writing a new class against an
existing interface."

## 7. Format dispatch

**Decision**: A `DataSourceReader` `Protocol` (`read() -> pandas.DataFrame`) with one
implementation per format — `CsvReader`, `JsonReader` — selected by file extension in the
`Dataset` abstraction. No `if format == "csv" elif format == "json"` branching outside that
one selection point.

**Rationale**: Constitution Engineering Principle 3 mandates polymorphic format dispatch so a
third format is additive.

**Alternatives considered**: A single reader function with format branching inside was
rejected per Engineering Principle 3.

## 8. JSON data source shape

**Decision**: A JSON data source is expected to be a top-level array of flat (non-nested)
objects. The reader loads it as a list of dicts and takes the union of keys across the
sampled records as the field set (User Story 2, Acceptance Scenario 2), filling absent keys
with `None` for records that lack them, without recursively flattening nested objects/arrays.

**Rationale**: Nothing in the spec's requirements, scenarios, or domain description mentions
nested JSON structures — "tables"/"records" framing and the CSV-parity requirements (FR-004)
imply flat tabular records. Deferring nested-object flattening keeps the reader simple
(constitution VII: no unused generality ahead of demonstrated need).

**Alternatives considered**: Using `pandas.json_normalize` to auto-flatten arbitrary nesting
was rejected as solving a problem not present in the spec's scope; it can be added later as
an additive change to `JsonReader` without touching the `DataSourceReader` protocol.

## 9. Error signaling across the capability boundary

**Decision**: Each capability raises a typed exception (from a shared `exceptions` module:
`DataSourceNotFoundError`, `UnreadableSourceError`, `FieldNotFoundError`,
`NumericTypeError`, `IdentifierCollisionError`) rather than encoding errors inside the
pydantic response model. Translating these exceptions into whatever shape an agent-facing
`@agent.tool` needs (e.g. a `ModelRetry`) is wiring-layer responsibility, out of this
feature's scope (§1).

**Rationale**: Keeps success-path pydantic models clean (Engineering Principle 5: only
validated data crosses the boundary) and keeps the capability functions plain and
unit-testable (Engineering Principle 6) — a test simply asserts the right exception type and
message is raised, independent of how a future wiring layer surfaces it to a model.

**Alternatives considered**: An `Ok[T] | Error` discriminated-union return type was
considered but rejected as unnecessary ceremony for a Python library boundary where
exceptions are idiomatic; nothing in the spec requires errors to be returned rather than
raised.

## 10. Type checker

**Decision**: `pyright`, run in CI (Engineering Principle 10).

**Rationale**: Constitution allows either mypy or pyright. pyright needs no plugin to
understand pydantic v2's generated `__init__`/validators, matches the tooling used by the
pydantic-ai project this codebase will eventually integrate with, and its typed-Protocol
checking (used heavily here for `QueryEngine`/`DataSourceReader`) is fast and strict by
default.

**Alternatives considered**: mypy was considered — also viable, would work equally well with
pydantic v2 — but pyright was chosen for consistency with the pydantic-ai ecosystem and
faster iteration in CI/editor.

## 11. Testing framework

**Decision**: `pytest`, with one contract-test module per capability (mirroring the spec's
Acceptance Scenarios 1:1) plus unit tests for `numeric.py` and the `Dataset` abstraction's
identifier/collision logic. Fixture datasets (mixed CSV/JSON, malformed files, nested
folders, mixed-locale numeric fields) live under `tests/fixtures/`.

**Rationale**: Constitution Principle IV requires tests to read as a specification; naming
contract tests directly after acceptance scenarios (e.g.
`test_discovery_flags_unreadable_source`) makes the traceability explicit. pytest is the de
facto standard for this ecosystem and pairs cleanly with pydantic v2.

**Alternatives considered**: unittest's `TestCase` classes were rejected — more boilerplate,
weaker fixture ergonomics, no material benefit here.
