# Feature Specification: Richer Aggregation (Filters, Functions, Ordering, Limit)

**Feature Branch**: `007-aggregate-rows-enhancements`

**Created**: 2026-09-24

**Status**: Draft

**Input**: User description: "I need to add a 'filters' field to the aggregate_rows tool, allowing the agent to aggregate only the filtered rows. I also want to add 'mean', 'max', 'min' and 'count_distinct' functions to aggregate_rows. Finally, I want to add 'order_by' and 'limit' parameters to aggregate_rows."

## Clarifications

### Session 2026-09-24

- Q: When no sort order is given (or groups tie on every sort key), what order should groups come back in? → A: Ascending by grouping values (compared like `order_by` on a grouping field, missing values last); ties on all sort keys are broken the same way.
- Q: When sorting by a grouping field, should numeric-looking fields sort as numbers? → A: Yes. Compare numerically (locale-aware, like `sum`) when the grouping field is numeric-like, otherwise as text.
- Q: Should the numeric-field check for `mean`/`min`/`max` (and range filters) look at the whole source or only at the filtered rows? → A: The whole source, the same classification schema inspection and row queries use; it applies even when the filters match no rows.

## User Scenarios & Testing *(mandatory)*

The "user" of the aggregation capability is the question-answering agent. It calls it while answering a natural-language question about a Brazilian open dataset. Today the agent can only group all rows of a source and compute `count` or `sum` per group. Many realistic questions need more than that: "total spending in 2023 by ministry", "average contract value per state", "which 5 municipalities received the most transfers", "how many distinct suppliers each agency hired". Without these capabilities the agent either can't answer or falls back to reading raw rows and doing arithmetic itself. Constitution Principle VI forbids that fallback: wherever a result can be computed mechanically, it must be.

### User Story 1 - Aggregate only the rows that match filters (Priority: P1)

The agent asks for an aggregation over a subset of a source's rows. It supplies filter conditions in the same form it already uses to query rows (equals, contains, numeric range). Only rows matching all conditions contribute to the groups and their aggregate values.

**Why this priority**: Most analytical questions are scoped ("in 2023", "in São Paulo", "contracts above R$ 1 million"). Without filtering, the agent can't answer them with the aggregation capability at all. This slice gives the most value on its own.

**Independent Test**: Aggregate a known fixture source with and without a filter. Check that the filtered result matches a hand-computed aggregation over only the matching rows.

**Acceptance Scenarios**:

1. **Given** a source with rows for years 2022 and 2023, **When** the agent groups by `orgao` and sums `valor` with the filter `ano equals 2023`, **Then** each group's sum includes only 2023 rows.
2. **Given** several filter conditions, **When** the agent aggregates, **Then** only rows satisfying all conditions (logical AND) are included, the same way row queries combine conditions.
3. **Given** filters that match no rows, **When** the agent aggregates, **Then** the result contains zero groups and no error.
4. **Given** a filter that names a field not present in the source, **When** the agent aggregates, **Then** the request is rejected with the same "field not found" error row queries produce, so the agent can correct itself.
5. **Given** a range filter on a field that isn't numeric-like, **When** the agent aggregates, **Then** the request is rejected with the same "not numeric" error row queries produce.
6. **Given** a request with no filters, **When** the agent aggregates, **Then** the result is identical to today's behavior.

---

### User Story 2 - Use mean, min, max and count_distinct (Priority: P2)

The agent asks for the average, minimum or maximum of a numeric field per group, or for the number of distinct values of any field per group.

**Why this priority**: These functions cover a large class of common questions: averages, extremes and "how many different X". Only `sum` and `count` exist today, so the agent can't compute these without doing arithmetic itself.

**Independent Test**: Run each new function over a fixture with known values, including locale-formatted numbers ("1.234,56") and missing values. Compare against hand-computed results.

**Acceptance Scenarios**:

1. **Given** a group whose numeric field holds "10", "20" and "30", **When** the agent requests `mean`, `min` and `max` of that field, **Then** the results are 20, 10 and 30.
2. **Given** a numeric field in Brazilian locale format (e.g. "1.234,56"), **When** the agent requests `mean`/`min`/`max`, **Then** values are interpreted the same way `sum` interprets them.
3. **Given** a group where some values of the field are missing, **When** the agent requests `mean`/`min`/`max`, **Then** missing values are ignored (not treated as zero).
4. **Given** a group where every value of the field is missing, **When** the agent requests `mean`/`min`/`max`, **Then** that result is reported as missing (null), not zero.
5. **Given** a text field such as `fornecedor`, **When** the agent requests `mean`/`min`/`max` on it, **Then** the request is rejected with the "not numeric" error that `sum` already produces.
6. **Given** a group where a field holds "A", "B", "A" and one missing value, **When** the agent requests `count_distinct` of that field, **Then** the result is 2.
7. **Given** any field, numeric-like or text, **When** the agent requests `count_distinct`, **Then** the request is accepted.

---

### User Story 3 - Order and limit the groups (Priority: P3)

The agent asks for the groups to be sorted by an aggregate result or a grouping field, ascending or descending. It can also cap the number of groups returned, e.g. to answer "top 10" questions or to keep a many-group result small.

**Why this priority**: "Top N" and "largest/smallest" questions are common. Ordering also keeps high-cardinality groupings (e.g. by municipality, ~5,570 values) from returning huge unsorted results that the agent then has to scan. It depends less on the other stories but adds the most value once filters and more functions exist.

**Independent Test**: Aggregate a fixture that produces a known set of groups, with an ordering and a limit. Check that the returned groups are the expected top N in the expected order and that truncation is reported.

**Acceptance Scenarios**:

1. **Given** an aggregation that produces 50 groups, **When** the agent orders by `sum_valor` descending with limit 5, **Then** exactly the 5 groups with the largest sums are returned, in descending order.
2. **Given** an ordering on a grouping field ascending, **When** the agent aggregates, **Then** groups are returned in ascending order of that field's value: text order for a text field (e.g. `uf`), numeric order for a numeric-like field (e.g. `mes` "1"…"12" gives 1, 2, …, 10, 11, 12).
3. **Given** several ordering keys, **When** the agent aggregates, **Then** groups are ordered by the first key, and ties are broken by the next key, and so on.
4. **Given** some groups whose ordering value is missing (null), **When** the agent orders by that value in either direction, **Then** those groups appear after all groups that have a value.
5. **Given** a limit smaller than the number of groups produced, **When** the agent aggregates, **Then** the result reports the total number of groups before the limit and marks the result as truncated.
6. **Given** a limit and no ordering, **When** the agent aggregates, **Then** the first N groups in the default group order (ascending by grouping values, in `group_by` order, missing values last) are returned, and truncation is reported.
7. **Given** an ordering key that is neither a grouping field nor the name of a requested aggregate result, **When** the agent aggregates, **Then** the request is rejected with an error that names the invalid key and lists the valid ones.
8. **Given** a limit of zero or a negative number, **When** the agent aggregates, **Then** the request is rejected as invalid.

---

### Edge Cases

- **Filters plus limit**: filters are applied first, then grouping, then aggregation, then ordering, then the limit. The limit counts groups, not rows.
- **Filters that match nothing, plus an invalid function**: `mean` on a text field is rejected with the not-numeric error even if the filters match no rows, because field types come from the whole source.
- **Empty source**: an empty source returns zero groups for every function. This matches today's behavior.
- **Unparseable numeric values in a numeric-like field**: `mean`/`min`/`max` skip values that can't be parsed as numbers, the same way `sum` does today.
- **`count` vs `count_distinct`**: `count` keeps its current meaning (number of rows in the group, missing values included). `count_distinct` counts distinct non-missing values of the named field.
- **`count_distinct` value matching**: values are compared exactly as they appear in the source. "São Paulo" and "SAO PAULO" count as two distinct values. No normalization is applied.
- **Ordering by a grouping field**: if the grouping field is numeric-like, its values are compared as numbers using the same locale-aware parsing `sum` uses (so "2" sorts before "10"). Values that can't be parsed are treated like missing values and sort last. Other grouping fields are compared as text. Either way, group values are still reported as text, as today.
- **Same function and field requested twice**: this produces a single result key, as today. Ordering by that key is unambiguous.
- **Limit larger than the number of groups**: all groups are returned and the result is not marked truncated.

## Requirements *(mandatory)*

### Functional Requirements

**Filtering**

- **FR-001**: The aggregation capability MUST accept an optional list of filter conditions. It MUST use the same condition types and semantics as the row-query capability: equals, contains, and numeric range, all combined with logical AND.
- **FR-002**: Only rows matching all filter conditions MUST contribute to grouping and to every aggregate value.
- **FR-003**: Filter conditions MUST be validated the same way the row-query capability validates them: unknown field → field-not-found error, range on a non-numeric field → not-numeric error.
- **FR-004**: When no rows match the filters, the capability MUST return an empty set of groups without error, as long as the request is otherwise valid. Validation errors (unknown field, non-numeric field) MUST still be raised when the filters match nothing.

**Aggregate functions**

- **FR-005**: The capability MUST support `mean`, `min`, `max` and `count_distinct` in addition to the existing `count` and `sum`.
- **FR-006**: `mean`, `min` and `max` MUST apply only to numeric-like fields. They MUST interpret values with the same locale-aware number parsing `sum` uses, and a non-numeric field MUST be rejected with the existing not-numeric error. Whether a field is numeric-like MUST be decided from the whole source, never from the filtered rows, using the same classification schema inspection reports. The same classification decides how a grouping field is compared when sorting (FR-010).
- **FR-007**: `mean`, `min` and `max` MUST ignore missing and unparseable values. When a group has no usable value, the result for that function MUST be reported as missing (null), not zero.
- **FR-008**: `count_distinct` MUST return the number of distinct non-missing values of the named field within each group, comparing values exactly as stored. It MUST accept both numeric-like and text fields.
- **FR-009**: Existing `count` and `sum` results MUST stay unchanged in meaning and naming. Result keys for new functions MUST follow the existing `<function>_<field>` naming pattern.

**Ordering and limit**

- **FR-010**: The capability MUST accept an optional ordered list of sort keys. Each key names either a grouping field or a requested aggregate result key and has a direction: ascending or descending. The default direction is ascending. Grouping-field values are compared numerically (locale-aware) when the field is numeric-like and as text otherwise. Aggregate results are compared numerically.
- **FR-011**: Groups MUST be sorted by the sort keys in order, with later keys breaking ties. Groups with a missing sort value MUST come after groups with a value, whatever the direction. When no sort keys are given, and to break ties that remain after all sort keys, groups MUST be ordered ascending by their grouping values (in `group_by` order, compared as for a grouping-field sort key, missing values last), so the result doesn't depend on the row order of the source.
- **FR-012**: A sort key that doesn't match a grouping field or a requested aggregate result key MUST be rejected with an error that names the invalid key and lists the valid choices.
- **FR-013**: The capability MUST accept an optional positive-integer limit on the number of groups returned. Zero or negative limits MUST be rejected as invalid input.
- **FR-014**: The limit MUST be applied after filtering, grouping, aggregation and ordering.
- **FR-015**: Every aggregation result MUST report the total number of groups before the limit and whether the returned groups were truncated, like row-query results already do.

**Compatibility and agent exposure**

- **FR-016**: Filters, ordering and limit MUST all be optional. A request that uses none of them and only `count`/`sum` MUST produce the same groups and values as before this feature. Only the order of groups may change: it now follows the default group order in FR-011 instead of first appearance in the source.
- **FR-017**: The description of the aggregation tool that the agent sees MUST document the new parameters and functions. It MUST state that filtering happens before aggregation and give the result-key naming convention used for ordering.
- **FR-018**: All new validation errors MUST come back to the agent as correctable errors that it can retry, like existing data-access errors, not as run failures.
- **FR-019**: The core aggregation logic MUST stay usable without the agent framework, so the automated test and validation harness can call it directly.

### Key Entities

- **Aggregation request**: what the agent asks for. It has grouping fields (required, at least one), aggregate specifications (required, at least one), and optionally filter conditions, sort keys and a limit.
- **Aggregate specification**: a value field plus a function, one of `count`, `sum`, `mean`, `min`, `max`, `count_distinct`. Its result key is `<function>_<field>`.
- **Filter condition**: the same equals / contains / range condition the row-query capability already uses.
- **Sort key**: a reference to a grouping field or an aggregate result key, plus a direction (ascending/descending).
- **Aggregation result**: the source identifier, the list of groups (each with grouping values and aggregate results, which may now be missing), the total group count before the limit, and a truncation flag.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every aggregation request valid before this feature returns identical groups and values afterwards. This is verified by the existing aggregation test suite passing unchanged, apart from the added count/truncation fields and the now-deterministic group order.
- **SC-002**: For each new function, the results on a fixture with locale-formatted and missing values match hand-computed expected values exactly.
- **SC-003**: A question of the form "top N groups by an aggregate, restricted to a subset of rows" can be answered with a single aggregation call instead of a row query followed by manual computation.
- **SC-004**: On the project's question testset, the number of answers whose numbers the agent computed itself rather than getting from a tool doesn't go up, and questions that need filtered, averaged, extreme, distinct-count or top-N aggregates are answered correctly at least as often as before. Both are measured by comparing testset runs before and after the change.
- **SC-005**: Every invalid request introduced by this feature (bad sort key, bad limit, non-numeric field for mean/min/max, unknown filter field) produces an error message that names the offending input. That lets the agent correct itself within its existing retry budget.

## Assumptions

- **Grouping stays required**: at least one grouping field is still needed. Aggregating a whole filtered subset as a single group ("total spending in 2023") is out of scope for this feature. The agent can still get it by grouping on a field it filtered to a single value.
- **Filter semantics are reused, not extended**: no new condition types (OR logic, "not equals", date ranges) are added. Filtering uses exactly the conditions row queries support today.
- **Ascending is the default sort direction**, following common query-language convention. The agent states "descending" explicitly for "top N" questions.
- **Missing sort values go last** in both directions, so "top N" results never begin with groups that have no value.
- **No default limit is imposed**: without a limit, all groups are returned, as today. Adding a default cap would change existing behavior and is out of scope.
- **`min`/`max` are numeric only**: text and date-like fields are not supported, because lexicographic ordering of values like "31/12/2022" vs "01/01/2023" would give misleading answers.
- **Result shape change is additive**: the only additions to results are the total-group-count and truncation fields and the fact that result values can now be null. Consumers that stored earlier results (e.g. recorded testset runs) are not migrated.
- The existing step budget and retry behavior for agent tool calls apply unchanged to the richer aggregation calls.
