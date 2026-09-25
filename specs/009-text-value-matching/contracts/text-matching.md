# Contract: Text Filter Matching (`equals` / `contains`)

Delta to 001 [contracts/query.md](../../001-data-access-tools/contracts/query.md) and 007
[contracts/aggregation.md](../../007-aggregate-rows-enhancements/contracts/aggregation.md).
The change applies to `query_rows` filters and `aggregate_rows` `request.filters` alike,
because both go through `PandasQueryEngine._condition_mask` (FR-005). Models:
[data-model.md](../data-model.md). Rationale: [research.md](../research.md) R1–R3.

```python
def query_rows(dataset, identifier, filters, *, text_matching=TextMatchingConfig()) -> RowQueryResult: ...
def aggregate_rows(dataset, identifier, request, *, text_matching=TextMatchingConfig()) -> AggregationResult: ...
```

The new keyword argument has a default, so every existing call is valid as is.

## Normalization (FR-001)

`normalize(s)`: NFKD → drop combining marks → `casefold()` → each run of non-word
characters or `_` becomes one space → collapse and trim whitespace.

| Input | `normalize` |
|---|---|
| `"Agência Espacial Brasileira"` | `agencia espacial brasileira` |
| `"Projeto CBERS-4"` | `projeto cbers 4` |
| `"Ministério da Ciência, Tecnologia, Inovações e Comunicações"` | `ministerio da ciencia tecnologia inovacoes e comunicacoes` |
| `"  Satélite   Sino-Brasileiro (CBERS) "` | `satelite sino brasileiro cbers` |
| `"-"`, `"..."` | `""` |
| `"2012"` | `2012` |

## Matching rules

Let `stored` be a non-missing stored value. Missing (`None`, NaN, empty or whitespace-only)
**never** matches either operator.

| Operator | Matches when |
|---|---|
| `equals` | `normalize(stored) == normalize(value)` (FR-002) |
| `contains` | every query word of `value` is a prefix of some word of `normalize(stored)`, in any order. Query words = `normalize(value).split()` minus stopwords, or all of them if only stopwords remain. No query words → matches every non-missing value. (FR-003) |

Stopwords come from the list named by `text_matching.stopwords` (default `pt_v1`).
`equals` never skips stopwords.

`range` conditions, field validation, error order and result caps are unchanged (FR-007).
Returned rows and groups hold raw stored values (FR-006).

## Behavioral requirements (traceability)

| Scenario | Filter → stored | Expected |
|---|---|---|
| US1-AS1 | `equals "agencia espacial brasileira"` → "Agência Espacial Brasileira" | match |
| US1-AS2 | `equals "projeto cbers 4"` → "Projeto CBERS-4" | match |
| US1-AS3 | `equals "Ministerio da Ciencia Tecnologia Inovacoes e Comunicacoes"` → "Ministério da Ciência, Tecnologia, Inovações e Comunicações" | match |
| US1-AS4 | `contains "desenvolvimento de satelite sino brasileiro"` → "Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS-3" | match |
| US1-AS5 | `equals "Agência Espacial"` → "Agência Espacial Brasileira" | **no** match |
| US1-AS6 | any `range` | same rows as before |
| US1-AS7 | a value that equalled a non-missing stored value exactly | same rows as before |
| Clarif. Q1 | `contains "satel"` → "Satélite" | match |
| Clarif. Q1 | `contains "4"` → "2014"; `contains "cbers 4"` → "Projeto CBERS-14" | **no** match |
| Edge | `contains "cbers 4"` → "Projeto CBERS-4A" | match |
| Edge | `contains "de"` (only stopwords) → "Desenvolvimento" | match ("de" is kept and starts "desenvolvimento") |
| Edge | `contains "..."` → any non-missing value | match; missing → no match |
| Edge | `equals "-"` → `"..."` | match (both normalize to `""`); → `""` (missing) no match |
| Edge | `equals "programa x"` → "Programa X" and "PROGRAMA X" | both match |
| Edge | `equals "2012"` on a numeric-like field | same rows as before |
| Edge | stored "Nº 5 – 10%" filtered with itself | match (a value always matches itself) |
| Existing | `contains "AL"` on customers → {"Alice"} | unchanged (001 US3.2 test) |

**Deliberate change**: before this feature, `equals ""` matched empty cells and
`contains ""` matched every row including empty ones. Both now exclude missing values
(spec Edge Cases). A test states this.
