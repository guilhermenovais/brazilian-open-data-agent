# Feature Specification: Data Access Tool Layer

**Feature Branch**: `001-data-access-tools`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Define the data-access tool layer for the dataset question-answering agent. This covers the tools an agent calls to explore and query a dataset.

#### Capabilities required

1. Discovery: list the files/tables available in a dataset.
2. Schema inspection: for a given file, return its columns/fields and a bounded content sample for a caller to decide how to query it.
3. Filtered row query: return rows matching a set of filter conditions (equality, contains, numeric range at minimum).
4. Aggregation: group rows by one or more fields and compute counts/sums/other aggregates over a value field.

Decide the exact tool boundaries and signatures (e.g., whether inspection and discovery are one tool or two) based on what gives the contract. Don't treat the above as fixed function names.

#### Domain requirements

1. Support CSV and JSON as the initial formats.
2. Numeric fields may be formatted with locale-specific separators (e.g., Brazilian `1.234,56`-style) that diff within the same dataset; querying and aggregating must numeric results regardless of source formatting."

## Clarifications

### Session 2026-09-17

- Q: What happens when a data source fails to parse (malformed CSV or invalid JSON)? → A: It still appears in discovery (flagged as unreadable); any inspection/query/aggregation on it returns a clear parse error. Other sources are unaffected.
- Q: How should a numeric field that mixes locale conventions within the same file (e.g., some rows `"1.234,56"`, others `"1,234.56"`) be handled? → A: Detect the locale convention per individual value, not per field; each value is normalized using whichever convention it unambiguously matches.
- Q: How should the system handle a data source too large to reasonably hold in memory in full? → A: Out of scope for this contract — all supported data sources are assumed to fit in memory; an oversized source is a configuration/deployment concern, not a capability requirement.
- Q: What happens when two data sources in the dataset would resolve to the same identifier? → A: Discovery fails with a clear, distinguishable error naming the colliding sources, rather than listing either.
- Q: How should a field be classified when only some sampled values look numeric and others don't? → A: Threshold-based — a field is "numeric-like" if a strong majority of sampled values parse as numeric; individual non-numeric values within it are skipped/excluded from numeric filtering and aggregation rather than erroring the whole field.
- Q: A dataset's real-world storage is a folder that can contain files and subfolders — how should this be represented to the tool layer? → A: The tool layer only ever sees a flat collection of data source files, never a folder/directory structure. The underlying physical location (a local folder today, a downloaded temp folder in the future) and any subfolder nesting within it are resolved and traversed entirely inside an internal dataset abstraction, which the discovery/inspection/query/aggregation capabilities depend on but have no knowledge of the details of.
- Q: Should the internal dataset abstraction discard subfolder structure entirely, or model the hierarchy? → A: The dataset abstraction MUST model the folder/subfolder hierarchy internally (it is not a flat bag of files). Discovery's result to the caller stays a flat list (no nested tree), but each stable identifier encodes the source's relative path within the dataset (e.g., `"reports/2024/sales.csv"`), so the hierarchy is reflected in the identifier even though the listing itself is not nested.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Discover Available Data (Priority: P1)

Before answering any question about a dataset, the agent needs to find out what files/tables actually exist in that dataset, so it knows where it could possibly look for an answer.

**Why this priority**: This is the entry point to every question-answering session. No other capability is usable until the agent knows what data sources exist.

**Independent Test**: Point the tool layer at a dataset containing a mix of CSV and JSON files and confirm the discovery capability alone returns an accurate, complete list of queryable data sources — with no dependency on any other capability being implemented.

**Acceptance Scenarios**:

1. **Given** a dataset containing three CSV files and one JSON file, **When** discovery is invoked, **Then** all four are listed as available data sources, each with a stable identifier and its format.
2. **Given** a dataset directory that also contains a non-data file (e.g., a readme), **When** discovery is invoked, **Then** that file is excluded from the reported list.
3. **Given** a dataset with no files, **When** discovery is invoked, **Then** an empty list is returned rather than an error.
4. **Given** a dataset containing one file that fails to parse (malformed CSV or invalid JSON), **When** discovery is invoked, **Then** that source is still listed with a flag indicating it is unreadable, and all other sources are listed normally.
5. **Given** a dataset whose underlying storage has files nested across subfolders, **When** discovery is invoked, **Then** all data source files are listed as a single flat collection (not a nested tree), with each identifier reflecting the source's relative path within the dataset (e.g., `"reports/2024/sales.csv"`).

---

### User Story 2 - Inspect Schema & Sample Before Querying (Priority: P2)

Before querying a specific data source, the agent needs to see its field names and a small sample of real content, so it can decide which fields are relevant and understand how values are actually formatted.

**Why this priority**: Depends on discovery (P1) to know which source to inspect. Without this, the agent must guess field names and formats, producing invalid or wrong queries. This is what lets the agent reason before acting.

**Independent Test**: Given a known data source identifier, request its schema and confirm the response includes field names and a bounded sample of real records — including any locale-formatted numbers as found in the source — without needing the query or aggregation capabilities.

**Acceptance Scenarios**:

1. **Given** a CSV file with headers and 10,000 rows, **When** schema inspection is invoked, **Then** it returns all field names and a sample capped at a fixed maximum number of records, not the full file.
2. **Given** a JSON file with heterogeneous records, **When** schema inspection is invoked, **Then** it returns the field names observed across the sampled records plus a representative sample.
3. **Given** a field containing Brazilian-formatted numbers (e.g., `"1.234,56"`), **When** schema inspection is invoked, **Then** the sample shows the value as found in the source, and the field is flagged as numeric-like so the caller knows it can be queried numerically.
4. **Given** an identifier that does not match any discovered data source, **When** schema inspection is requested, **Then** a clear not-found error is returned instead of partial or fabricated data.
5. **Given** a data source identifier flagged as unreadable during discovery, **When** schema inspection, a query, or an aggregation is requested against it, **Then** a clear parse error is returned instead of partial or fabricated data.

---

### User Story 3 - Query Rows Matching Specific Conditions (Priority: P3)

The agent needs to retrieve the specific rows that answer a factual question, filtered by one or more conditions — exact match, substring match, or numeric range.

**Why this priority**: This is the core fact-retrieval capability, answering concrete "which records have X" questions. It depends on schema inspection (P2) to know which fields exist and how to filter them.

**Independent Test**: Using a data source and field identified via discovery/inspection, submit a filter (including a numeric range on a locale-formatted field) and confirm the returned rows match — and only match — the stated condition, regardless of the source's number formatting.

**Acceptance Scenarios**:

1. **Given** an equality condition on a field, **When** the query runs, **Then** only rows with an exact match on that field are returned.
2. **Given** a "contains" condition on a text field, **When** the query runs, **Then** only rows whose field value contains the given substring (case-insensitive) are returned.
3. **Given** a numeric field stored as `"1.234,56"`-style strings, **When** a numeric range condition (e.g., between 1000 and 2000) is applied, **Then** rows are matched by true numeric value, not by lexical string comparison.
4. **Given** multiple filter conditions in a single request, **When** the query runs, **Then** only rows satisfying all conditions simultaneously are returned.
5. **Given** a filter that matches more rows than the result cap, **When** the query runs, **Then** the response is bounded and clearly indicates that more matches exist, rather than silently truncating without notice.
6. **Given** a filter referencing a field name that does not exist in the data source, **When** the query runs, **Then** a clear error identifies the invalid field rather than returning an empty or misleading result.
7. **Given** an identifier that does not match any discovered data source, **When** a row query is requested, **Then** a clear not-found error is returned instead of an empty or misleading result.
8. **Given** a data source identifier flagged as unreadable during discovery, **When** a row query is requested against it, **Then** a clear parse error is returned instead of partial or fabricated data.
9. **Given** a numeric range condition targeting a field that is not classified numeric-like, **When** the query runs, **Then** a clear error is returned instead of a silently empty or misleading result.

---

### User Story 4 - Aggregate Rows Into Grouped Summaries (Priority: P4)

The agent needs to answer summary/statistical questions — totals, counts, and averages per category — by grouping rows on one or more fields and computing aggregates over a value field.

**Why this priority**: Serves a different question class than row-level lookup (P3): summarization rather than retrieval. It depends on schema inspection (P2) and shares the numeric-normalization requirement proven by P3, making it the most complex capability to get right.

**Independent Test**: Using a known data source, group by one categorical field and compute a count and a sum over a locale-formatted numeric field, and confirm grouped totals are numerically correct regardless of source formatting.

**Acceptance Scenarios**:

1. **Given** rows with a categorical field and a numeric value field, **When** grouped by the categorical field with a count aggregate, **Then** each group's count matches the true number of rows belonging to that group.
2. **Given** a value field formatted with Brazilian-style separators, **When** grouped with a sum aggregate, **Then** the summed value is numerically correct, not a lexical or string-concatenation result.
3. **Given** more than one grouping field, **When** aggregation runs, **Then** results are broken out by the full combination of grouping field values.
4. **Given** a value field whose values are not numeric, **When** a sum aggregate is requested on it, **Then** a clear error is returned instead of a silently wrong number.
5. **Given** a data source with no rows, **When** aggregation runs, **Then** an empty set of groups is returned rather than an error.
6. **Given** a value field where some rows use `"1.234,56"`-style formatting and others use `"1,234.56"`-style formatting within the same source, **When** grouped with a sum aggregate, **Then** each value is normalized using the convention it unambiguously matches, and the summed value is numerically correct.
7. **Given** an identifier that does not match any discovered data source, **When** aggregation is requested, **Then** a clear not-found error is returned instead of an empty or misleading result.
8. **Given** a data source identifier flagged as unreadable during discovery, **When** aggregation is requested against it, **Then** a clear parse error is returned instead of partial or fabricated data.

---

### Edge Cases

- ~~What happens when a data source fails to parse (malformed CSV or invalid JSON)?~~ Resolved: see Clarifications — it is listed in discovery flagged as unreadable, and any attempt to inspect/query/aggregate it returns a clear parse error.
- ~~How does the system handle a numeric field that mixes locale conventions within the same file (e.g., some rows `"1.234,56"`, others `"1,234.56"`)?~~ Resolved: see Clarifications — locale convention is detected per individual value, and each value is normalized using whichever convention it unambiguously matches.
- What happens when a query or aggregation request references a field name that does not exist in the target data source?
- ~~How does the system respond when a data source is too large to reasonably hold in memory in full?~~ Resolved: see Clarifications — out of scope; all supported data sources are assumed to fit in memory.
- ~~What happens when two data sources in the dataset would resolve to the same identifier?~~ Resolved: see Clarifications — discovery fails with a clear, distinguishable error naming the colliding sources.
- ~~How does the system handle a numeric range or aggregation request on a field where only some sampled values look numeric and others don't?~~ Resolved: see Clarifications — a field is "numeric-like" if a strong majority of sampled values parse as numeric; individual non-numeric values within such a field are skipped/excluded from numeric filtering and aggregation rather than erroring the whole field.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a capability to list every queryable data source in a dataset, returning a stable identifier and format (CSV or JSON) for each.
- **FR-001a**: If a data source fails to parse (malformed CSV or invalid JSON), discovery MUST still list it with a flag indicating it is unreadable, and MUST NOT let its failure prevent other sources from being listed. Any subsequent inspection, query, or aggregation call against a source flagged unreadable MUST return a clear parse error rather than partial or fabricated data.
- **FR-001b**: The dataset abstraction MUST model the dataset's underlying folder/subfolder hierarchy internally rather than discarding it. Discovery MUST still return a flat (non-nested) list to the caller, but each stable identifier MUST reflect the data source's relative path within that hierarchy (e.g., `"reports/2024/sales.csv"`), so two sources with the same filename in different subfolders resolve to distinct identifiers. Identifiers MUST NOT expose or depend on absolute/physical storage details (e.g., an absolute filesystem path, a temp-download location) beyond this relative path — resolving an identifier to its actual physical storage is the responsibility of the internal dataset abstraction, never a concern of the discovery, inspection, query, or aggregation capabilities themselves.
- **FR-002**: System MUST provide a capability that, given a data source identifier, returns the list of that source's fields.
- **FR-003**: System MUST provide a capability that, given a data source identifier, returns a bounded sample of real records reflecting values as they appear in the source.
- **FR-004**: System MUST support both CSV and JSON as source formats across every discovery, inspection, query, and aggregation capability.
- **FR-005**: System MUST provide a capability to retrieve rows from a specified data source filtered by one or more conditions, combined so that all conditions must hold (logical AND).
- **FR-006**: The filtered row query capability MUST support, at minimum: equality conditions, substring ("contains") conditions on text fields, and numeric range conditions with independently optional lower and upper bounds.
- **FR-007**: System MUST provide a capability to group rows from a specified data source by one or more fields and compute aggregate values — at minimum, count and sum — over a specified value field per group.
- **FR-008**: The aggregation capability MUST support grouping by more than one field simultaneously, breaking results out by the full combination of grouping values.
- **FR-009**: System MUST detect and normalize locale-specific numeric formatting (including Brazilian-style values such as `"1.234,56"`) on a per-value basis, so that numeric range filtering and numeric aggregation always operate on the true numeric value regardless of how the source formatted it.
- **FR-010**: System MUST correctly normalize numeric fields even when different data sources within the same dataset — or different rows within the same field — use different locale conventions for numeric formatting, by detecting each value's convention independently rather than assuming one convention per field.
- **FR-011**: System MUST cap the number of records returned by a single filtered row query and by the sample returned during schema inspection, and MUST indicate when a query's true match count exceeds the returned amount.
- **FR-012**: System MUST return a clear, distinguishable error — never an empty or fabricated result — when a caller references a data source identifier, field name, or value field that does not exist.
- **FR-012a**: If two or more data sources within a dataset would resolve to the same stable (relative-path-based) identifier — e.g., due to case-insensitive filesystem collisions or a dataset composed from multiple merged physical roots — discovery MUST fail with a clear, distinguishable error naming the colliding sources, rather than listing either one or silently merging/overwriting.
- **FR-013**: System MUST return a clear, distinguishable error when a numeric operation (range filter, sum) is requested against a field whose values cannot be interpreted as numeric.
- **FR-013a**: A field MUST be classified as numeric-like if a strong majority of its sampled values parse as numeric; FR-013's error applies only when a field does not meet that threshold. Within a field classified as numeric-like, individual values that do not parse as numeric MUST be skipped/excluded from numeric range filtering and numeric aggregation rather than causing the whole field's operation to error.
- **FR-014**: The four capabilities MUST be usable as a progressive, no-prior-knowledge sequence: a caller can discover data sources without knowing their schema, inspect a schema without having queried it yet, and query or aggregate only after inspecting — with no capability requiring hidden knowledge from a step the caller hasn't performed.

### Key Entities

- **Dataset**: The bounded collection of data sources the tool layer operates over for a given agent session; the unit that discovery enumerates. The dataset abstraction models the underlying folder/subfolder hierarchy internally (it is not a flat bag of files); discovery exposes that as a flat (non-nested) list to callers, with each data source's stable identifier reflecting its relative path within the hierarchy. The physical storage location (a local folder today, a downloaded temp directory in the future) is resolved entirely inside the dataset abstraction and is never a concern of the four capabilities.
- **Data Source**: One queryable unit within a dataset (one CSV file or one JSON file/array), identified by a stable identifier and a format; may be flagged unreadable if it fails to parse.
- **Field**: A named attribute within a data source, with a type as observed from sampled content (e.g., text, numeric-like, other). Classified as numeric-like when a strong majority of its sampled values parse as numeric; individual non-numeric values within such a field are excluded from numeric operations rather than disqualifying the field.
- **Content Sample**: A bounded set of real records from a data source, used by a caller to understand actual value formatting before querying.
- **Filter Condition**: One constraint (equality, contains, or numeric range) applied to a named field during a row query; multiple conditions in one request combine with logical AND.
- **Row Result**: The bounded set of records returned by a filtered row query, with an indicator of whether more matches exist beyond the cap.
- **Aggregation Request**: A grouping specification (one or more group-by fields) plus one or more aggregate computations over a named value field.
- **Aggregation Result**: The set of per-group computed values produced by an aggregation request.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given a dataset the agent has never seen, the agent can determine the complete list of available data sources using only the discovery capability, with no prior knowledge of the dataset's contents.
- **SC-002**: For any data source in a supported format, a caller can determine its fields and see real sample content in a single inspection call, without separately loading or scanning the full source.
- **SC-003**: Filtered row queries return exactly the matching rows for equality, contains, and numeric-range conditions across both CSV and JSON sources, including sources with locale-formatted numeric fields, on 100% of test cases.
- **SC-004**: Aggregation results (counts and sums) are numerically correct on 100% of test cases regardless of whether the source data used period-decimal or comma-decimal formatting.
- **SC-005**: A caller referencing a non-existent data source, field, or an invalid numeric operation receives a clear, actionable error in the same response — with zero observed cases of silently returning empty or fabricated data instead.
- **SC-006**: Schema-sample and row-query response sizes stay within a fixed, predictable bound regardless of source file size, so a caller never receives an unbounded dump of an entire large source.

## Assumptions

- A "dataset" is a fixed, bounded collection of data sources made available to the tool layer for a given agent session; discovering datasets outside that configured scope is out of scope for this contract. The real-world storage backing a dataset (today, a local folder that may itself contain subfolders; later, a location a dataset is downloaded to) is modeled and traversed by a separate internal dataset abstraction, which this contract depends on but does not define. That abstraction represents the folder/subfolder hierarchy internally (it is not discarded); the four capabilities themselves interact only with a flat list of data sources whose stable identifiers reflect relative path within that hierarchy, never an absolute or physical storage location.
- Every data source in scope for this contract is assumed to fit in memory in full; sources too large to load in memory are a configuration/deployment concern outside this contract, not a capability the tool layer must support (e.g., via streaming or chunked processing).
- Filter conditions within a single row-query request combine with logical AND only; OR or mixed logic across conditions is out of scope for this initial contract.
- Field type ("numeric-like" vs. text) is inferred from sampled content rather than a declared schema, since CSV/JSON sources in this domain are not assumed to carry explicit type metadata.
- Locale-specific numeric normalization is detected per individual value from sampled/observed content; callers are not required to pre-declare which locale convention a field or value uses.
- Bounded sample and row-query result sizes use a fixed, reasonable default cap for this initial contract, rather than being caller-configurable per call.
- Required aggregate functions are count and sum; additional aggregates (e.g., average, min, max) are natural extensions but not required by this contract's initial scope.
- The tool layer is read-only: none of the four capabilities modify the underlying dataset files.
