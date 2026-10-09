# Contract: Value Suggestions on Empty Results

Applies to `query_rows` and `aggregate_rows` in `data_access.capabilities`. Models
(`ValueSuggestion`, `SuggestedValue`, `value_suggestions`): [data-model.md](../data-model.md).
Rationale: [research.md](../research.md) R4.

## When suggestions are attached

The steps below run after the existing pipeline, and only when the result is empty:
`total_match_count == 0` (`query_rows`) or `total_group_count == 0` (`aggregate_rows`).
Errors are raised exactly as before and in the same order. Suggestions never replace an
error.

1. Let `text_conditions` = the `equals`/`contains` conditions of the request, in request
   order. If there are none, `value_suggestions` is absent.
2. For each text condition, apply it **alone** to the unfiltered source with the same
   matcher. If it matches at least one row, it gets no entry.
3. Every other text condition gets one `ValueSuggestion{field, op, value, candidates}`.
4. `value_suggestions` = the list of those entries, in request order. It may be `[]`.

A result with at least one row or group never has the `value_suggestions` key (FR-013).
For `aggregate_rows`, `limit` does not matter: a limit is ≥ 1, so a result with 0 groups
before the limit also has 0 after it.

## Ranking candidates (FR-009 to FR-011)

For the condition's field, over its distinct non-missing stored values:

```text
query words  = query_words(condition.value)                     # same as contains
tokens(v)    = words(v) + [acronym(v)]                          # acronym skipped if ""
overlap(v)   = |{ w in query words : some t in tokens(v) starts with w }|
candidates   = [v for v if overlap(v) >= 1]
order        = overlap desc, row_count desc, v asc (code point)
keep         = first text_matching.max_suggestions
```

The ordering is total, so the same source and request always give the same list.

## Behavioral requirements (traceability)

| Scenario | Setup | Expected `value_suggestions` |
|---|---|---|
| US2-AS1 | `nome_unidade equals "AEB"`, values include "Agência Espacial Brasileira" | one entry; its first candidate is "Agência Espacial Brasileira", `overlap=1` |
| US2-AS2 | `contains "satélite CBERS 5"`; values "Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS-4", "Projeto CBERS-3" | the first value (overlap 2) before the second (overlap 1) |
| US2-AS3 | `[equals A (matches alone), equals B (matches nothing)]` | exactly one entry, for B |
| US2-AS4 | two conditions, each matches alone, combination empty | `[]` |
| US2-AS5 | value shares no word or acronym with any stored value | one entry with `candidates: []` |
| US2-AS6 | any non-empty result | key absent |
| US2-AS7 | only a `range` condition, 0 rows | key absent |
| FR-011 | more than `max_suggestions` values overlap | exactly `max_suggestions` candidates |
| FR-011 | two candidates with equal overlap | higher `row_count` first; then code-point order |
| Edge | a field with missing values | missing values are never candidates |
| Edge | `aggregate_rows` with 0 groups | same entries as `query_rows` with the same filters |
| SC-002 | on `dados_gerais/tb_geral.csv`: "AEB" (`nome_unidade`) | intended value at rank 1 |

## Example (serialized tool result)

```json
{
  "identifier": "dados_gerais/tb_geral.csv",
  "rows": [],
  "returned_count": 0,
  "total_match_count": 0,
  "truncated": false,
  "value_suggestions": [
    {
      "field": "nome_unidade",
      "op": "equals",
      "value": "AEB",
      "candidates": [
        {"value": "Agência Espacial Brasileira", "overlap": 1, "row_count": 301}
      ]
    }
  ]
}
```
