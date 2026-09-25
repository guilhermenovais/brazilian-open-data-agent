# Data Model: Forgiving Text Matching and Value Suggestions

Phase 1 output for [plan.md](./plan.md). All models are pydantic v2 (Eng. 5). "New" marks
a new model, "+" a field added to an existing model. No existing field is removed, renamed
or retyped.

## Configuration

### `TextMatchingConfig` (new, `data_access/text_matching.py`)

Frozen. The typed settings for this feature (FR-016, research.md R6).

| Field | Type | Default | Rule |
|---|---|---|---|
| `value_list_threshold` | `int` | `30` | `ge=0`. A field is listed when `distinct_count <= value_list_threshold`. `0` lists nothing. |
| `max_suggestions` | `int` | `5` | `ge=1`. Maximum candidates per zero-match condition. |
| `stopwords` | `str` | `"pt_v1"` | Must name a file `data_access/stopwords/<name>.txt`. Validated on construction. |

Carried by:

- `AgentSettings.text_matching: TextMatchingConfig` (+, default factory)
- `AgentDeps.text_matching: TextMatchingConfig` (+, default factory, dataclass field)
- `TestRun.text_matching: TextMatchingConfig | None = None` (+, `None` = pre-009 run)
- `ConversationRun.text_matching: TextMatchingConfig | None = None` (+, same)

### Stopword list (new artifact, `data_access/stopwords/pt_v1.txt`)

UTF-8 text, one word per line. Blank lines and lines starting with `#` are ignored. Words
are normalized on load, so the file may use accents ("à", "até"). Named versions are never
edited in place. A changed list is a new file (`pt_v2.txt`) (Eng. 8, FR-004).

### `MatchRules` (new, internal, `data_access/text_matching.py`)

Frozen dataclass, not a boundary model: `stopwords: frozenset[str]`. Built from a config by
`MatchRules.from_config(config)`. It is what `PandasQueryEngine(rules)` and the ranking
function receive. Its pure functions:

| Function | Result |
|---|---|
| `normalize(text) -> str` | research.md R1. Comparison form only, never returned to a caller (FR-006). |
| `words(text) -> list[str]` | `normalize(text).split()` |
| `query_words(value) -> list[str]` | `words(value)` minus stopwords, or all of `words(value)` if that is empty (FR-003) |
| `acronym(text) -> str` | First letter of each non-stopword word of `words(text)`, joined. Empty if none. |
| `equals(stored, value) -> bool` | `normalize(stored) == normalize(value)` (FR-002) |
| `contains(stored, value) -> bool` | Every query word is a prefix of some word of `stored`. True when there are no query words. (FR-003) |
| `overlap(stored, value) -> int` | Count of query words that are a prefix of some word of `stored` or of `acronym(stored)` (FR-009/010) |

Missing values are handled by the caller (engine, ranking), never passed to these
functions: a missing stored value never matches and is never a candidate.

## Tool results

### `FieldInfo` (+)

| Field | Type | Meaning |
|---|---|---|
| `name` | `str` | unchanged |
| `type` | `"numeric_like" \| "text"` | unchanged |
| `distinct_count` (+) | `int` | Distinct non-missing raw values of this field across the **whole** source. |
| `values` (+) | `list[str] \| None` | All those values, raw, sorted by code point, when `distinct_count <= value_list_threshold`. Otherwise `null` (not listed: too many values). |

Invariant: `values is None` ⇔ `distinct_count > value_list_threshold`. When `values` is a
list, `len(values) == distinct_count`.

### `SchemaInspectionResult` (+)

| Field | Type | Meaning |
|---|---|---|
| `identifier`, `fields`, `sample` | unchanged | Computed exactly as before (FR-017). |
| `value_list_threshold` (+) | `int` | The threshold used, so a `null` `values` can be read as "more than N values". |

### `SuggestedValue` (new, `data_access/models.py`)

| Field | Type | Meaning |
|---|---|---|
| `value` | `str` | A distinct stored value of the field, exactly as stored (FR-006). |
| `overlap` | `int` | `ge=1`. Query words of the condition that start a word or the acronym of `value`. |
| `row_count` | `int` | `ge=1`. Rows of the source holding exactly this value. |

### `ValueSuggestion` (new, `data_access/models.py`)

One per `equals`/`contains` condition that matches no rows of the source on its own
(FR-008, FR-012).

| Field | Type | Meaning |
|---|---|---|
| `field` | `str` | The condition's field. |
| `op` | `"equals" \| "contains"` | The condition's operator. |
| `value` | `str` | The condition's value, as sent. |
| `candidates` | `list[SuggestedValue]` | At most `max_suggestions`. Ordered by `overlap` desc, `row_count` desc, `value` asc (code point). **Empty** means "no close values found" (US2-AS5). |

### `RowQueryResult` (+) and `AggregationResult` (+)

| Field | Type | Meaning |
|---|---|---|
| `value_suggestions` (+) | `list[ValueSuggestion] \| None` | `Field(default=None, exclude_if=lambda v: v is None)`. Set only when the result is empty (`total_match_count == 0` / `total_group_count == 0`) **and** the request has at least one text condition. Then it holds one entry per text condition that matches nothing on its own, which may be an empty list (US2-AS4). |

Because of `exclude_if`, a result without suggestions serializes exactly as before this
feature, with no `value_suggestions` key (FR-013). An empty list (`[]`) is serialized. It
means "every text condition matches rows on its own, so the combination is what matches
nothing".

States of an empty result's `value_suggestions`:

| Request | `value_suggestions` |
|---|---|
| No filters, or only range filters | absent |
| Text conditions, each matches rows alone | `[]` |
| At least one text condition matches nothing alone | one `ValueSuggestion` per such condition |

## Filter conditions (+ descriptions only)

`EqualsCondition.value` and `ContainsCondition.value` gain `Field(description=…)` text
(research.md R7). Their types, discriminator and validation are unchanged. `RangeCondition`
is unchanged (FR-007).

## Relationships

```text
TextMatchingConfig ──(from_config)──▶ MatchRules ──▶ PandasQueryEngine(rules)
        │                                  └────────▶ rank_candidates(...)
        ├── AgentSettings.text_matching ──▶ AgentDeps.text_matching ──▶ tools ──▶ capabilities(text_matching=…)
        └── TestRun / ConversationRun.text_matching   (recorded copy of the value used)

RowQueryResult / AggregationResult ──0..n──▶ ValueSuggestion ──0..max──▶ SuggestedValue
SchemaInspectionResult ──▶ FieldInfo{distinct_count, values}
```
