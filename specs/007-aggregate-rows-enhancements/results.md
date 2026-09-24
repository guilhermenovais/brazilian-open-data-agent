# Results: Richer Aggregation (007)

Evidence for SC-003 / SC-004 (Principles I–II). See quickstart.md §2–§4 and research.md §10.

## Baseline

- **Commit**: `6636991` (pre-feature).
- **Run file**: `data/testset_runs/20260924T121028315459Z.json` (testset
  `data/testsets/orcamentos-aeb-csv.json`, content hash `81e631b8…70ce`).
- **Settings**: `--model gpt-5.4-nano`, `--base-url https://api.openai.com/v1`,
  `--max-attempts 3` (retry policy: initial wait 2.0 s, ×2.0 backoff, max wait 60 s).
- **Provenance note**: this run was recorded before `6636991` was committed (run 12:10Z,
  commit 14:30Z), but it already carries the `retry_policy` that `6636991` introduces, so it
  was made from that commit's working tree. No fresh run was possible during implementation
  (no model credentials in the session). Re-run it at `6636991` if a strictly clean baseline is
  needed.

### Match rates

| Scope | Questions | Match rate | Status counts |
|-------|-----------|------------|---------------|
| Overall | 50 | 0.64 | matched 32, needs_review 16, not_matched 1, errored 1 |
| calculation | 17 | 0.706 | matched 12, needs_review 3, not_matched 1, errored 1 (RateLimitError) |
| single-lookup | 20 | 1.00 | matched 20 |
| multiple-files | 10 | 0.00 | needs_review 10 |
| edge-cases | 3 | 0.00 | needs_review 3 |

### Aggregation-dependent questions

All in category `calculation`, source `dados_gerais/tb_geral.csv`. "Calls" is the number of
`query_rows` + `aggregate_rows` calls in the baseline trace.

| Id | Needs | Baseline outcome | Calls |
|----|-------|------------------|-------|
| 21–24, 27 | filtered sum (one year) | matched | 1 |
| 25, 26 | filtered sum (one year) | matched | 2 |
| 28 | filtered row / distinct count | matched | 4 |
| 29 | filtered count_distinct | matched | 9 |
| 30 | filtered mean | matched | 9 |
| 31 | filtered mean | errored (RateLimitError) | 0 |
| 32 | filtered top-1 (max) | needs_review | 3 |
| 33 | filtered top-1 (max) | needs_review | 9 |
| 34 | filtered top-1 (max) | needs_review | 8 |
| 35 | filtered sum (year range + text) | matched | 9 |
| 36 | unfiltered sum | matched | 3 |
| 37 | filtered count_distinct (years) | not_matched | 4 |

Answers whose numbers appear in no tool result (hand count from `steps[].result_summary`):
to be filled in together with the post-feature run (T035), so that both counts are made the
same way.

## Direct capability check

Run on 2026-09-24 against the feature working tree with
`PYTHONPATH=src python t033.py` (script below, summarized). Source
`data/datasets/orcamentos-aeb-csv` → `dados_gerais/tb_geral.csv`.

Request: `group_by=["nome_acao"]`, aggregates `sum(pago)`, `mean(pago)`,
`count_distinct(id_orcamento)`, `filters=[data_ano equals "2005"]`,
`order_by=[sum_pago desc]`, `limit=3`.

```text
Participação Brasileira no Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS {'sum_pago': 46219753.0, 'mean_pago': 46219753.0, 'count_distinct_id_orcamento': 1}
Desenvolvimento e Lançamento de Satélites de Aplicação {'sum_pago': 15707599.0, 'mean_pago': 15707599.0, 'count_distinct_id_orcamento': 1}
Formação de Astronautas {'sum_pago': 11950000.0, 'mean_pago': 11950000.0, 'count_distinct_id_orcamento': 1}
total_group_count 32 truncated True
non-increasing: True
query_rows rows: 1 hand sum: 46219753.0 matches: True
distinct actions in 2005 via query_rows: 32 truncated: False
InvalidSortKeyError: Sort key 'nope' is not valid for data source 'dados_gerais/tb_geral.csv'; valid keys: ['nome_acao', 'sum_pago']
NumericTypeError: Field 'nome_acao' in data source 'dados_gerais/tb_geral.csv' is not numeric-like
ValidationError: Input should be greater than or equal to 1
```

- 3 groups, sums non-increasing. `total_group_count == 32` equals the number of distinct
  actions that `query_rows` returns for 2005 (untruncated), and `truncated is True`.
- The top sum equals the hand-summed `query_rows` result for the same filter plus action,
  and it is the expected answer of testset question 32 (`46219753`), obtained with one call.
- The three documented errors are raised: `InvalidSortKeyError` (listing the valid keys),
  `NumericTypeError` (`mean` on a text field), and `pydantic.ValidationError` (`limit=0`).

## Agent end-to-end

_Pending (T034)._

## Post-feature testset

_Pending (T035)._
