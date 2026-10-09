# Quickstart: Validating Forgiving Text Matching and Value Suggestions

This guide checks the feature end to end. Interfaces are in [contracts/](./contracts/),
models are in [data-model.md](./data-model.md), and the evaluation design is in
[research.md](./research.md) R8.

## Prerequisites

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
```

For the live track: a local vLLM serving `Qwen/Qwen3-8B-AWQ` at `http://localhost:8000/v1`
(the 008 evidence target).

## 1. Offline track (CI gate, no model calls)

```bash
pytest tests/contract tests/unit -v
pyright src/
```

| Scenario | Test | Expected |
|---|---|---|
| Normalization, `equals`/`contains` rules, stopwords, acronym, overlap (FR-001–004, 009–010) | `tests/unit/data_access/test_text_matching.py` | every row of [contracts/text-matching.md](./contracts/text-matching.md) holds at the function level |
| Filters on a fixture with accented/hyphenated names (US1, FR-005) | `tests/contract/data_access/test_text_matching_filters.py` (fixture `tests/fixtures/data_access/sample_dataset/budget_actions.csv`) | `query_rows` and `aggregate_rows` return the hand-computed row sets |
| Suggestions on empty results (US2) | `tests/contract/data_access/test_value_suggestions.py` | every row of [contracts/value-suggestions.md](./contracts/value-suggestions.md) |
| Value lists (US3) | `tests/contract/data_access/test_inspection.py` (+ cases) | every row of [contracts/schema-inspection.md](./contracts/schema-inspection.md) |
| Existing exact/range/aggregation/inspection behavior (FR-007, FR-017, SC-006) | existing `test_query.py`, `test_aggregation.py`, `test_inspection.py`, `test_query_engine.py` | pass **unedited** |
| Tool descriptions (FR-018) | `tests/unit/qa_agent/test_tools_description.py` | new facts present; 007 assertions still pass |
| Prompts untouched (FR-018) | `tests/contract/qa_agent/test_standalone_unchanged.py`, `tests/unit/qa_agent/test_prompt_loader.py` | pass unedited |
| Run records carry `text_matching` (FR-016) | `tests/contract/testset_runner/test_run_testset.py`, `test_run_conversations.py`, `tests/unit/testset_runner/test_store.py` | value round-trips; pre-009 files (`tests/fixtures/testset_runner/pre-006-run.json`) load with `None` |

Check that the existing suites pass unedited:

```bash
git diff --stat main -- tests/contract/data_access/test_query.py \
  tests/contract/data_access/test_aggregation.py tests/unit/data_access/test_query_engine.py
# → no changes (test_inspection.py gains cases, but no existing case is edited)
```

## 2. Mechanism check on the real dataset (SC-002, SC-003)

```bash
python - <<'EOF'
from data_access.dataset import Dataset
from data_access.capabilities import inspect_schema, query_rows
from data_access.models import EqualsCondition, ContainsCondition
ds = Dataset("data/datasets/orcamentos-aeb-csv")
src = "dados_gerais/tb_geral.csv"
for c in [EqualsCondition(field="nome_unidade", value="AEB"),
          EqualsCondition(field="nome_acao", value="desenvolvimento do satélite Amazônia-1"),
          ContainsCondition(field="nome_acao", value="satélite CBERS 3")]:
    r = query_rows(ds, src, [c])
    print(c.value, r.total_match_count, r.model_dump(exclude_none=True).get("value_suggestions"))
for f in inspect_schema(ds, src).fields:
    print(f.name, f.distinct_count, f.values)
EOF
```

Expected:

- `AEB`: 0 rows, first candidate "Agência Espacial Brasileira".
- Amazônia-1: matches directly (5 rows), no suggestions.
- `satélite CBERS 3`: matches the CBERS-3 action rows.
- `nome_unidade` (2), `nome_programa` (13), `data_ano` (20) have full lists; `nome_acao`
  (116) and the monetary fields show `None`.

## 3. Live evaluation (FR-019, SC-004, SC-005)

Same conditions as 008: same model, `--max-attempts 3`, history limit 16000. Neither prompt
is changed.

```bash
python -m testset_runner.cli run-conversations \
  --testset data/testsets/conversations/orcamentos-aeb-csv-conversations.json \
  --model Qwen/Qwen3-8B-AWQ --base-url http://localhost:8000/v1 --api-key x \
  --max-attempts 3 --history-char-limit 16000
# → report ends with "Text matching: value_list_threshold=30, max_suggestions=5, stopwords=pt_v1"

python -m testset_runner.cli run \
  --testset data/testsets/orcamentos-aeb-csv-10.json \
  --model Qwen/Qwen3-8B-AWQ --base-url http://localhost:8000/v1 --api-key x --max-attempts 3

python -m testset_runner.cli compare 20260925T100203429266Z <new-standalone-run-id>
# SC-005: newly_failing = 0

python specs/009-text-value-matching/analyze_runs.py \
  --before 20260925T095751382002Z --after <new-conversation-run-id>
# prints per-category before/after, per-turn transitions, zero-row text-filter audit,
# inspect_schema size before/after
```

| Criterion | Where to read it | Target |
|---|---|---|
| SC-004 (a) | `analyze_runs.py` category table, `follow-up-metric` | ≥ 2/3 (from 0/3) |
| SC-004 (b) | `analyze_runs.py` zero-row audit | no scored turn failed with an empty text-filter result whose value exists in the source |
| SC-005 | `compare` output | 0 `newly_failing` |
| FR-019 size | `analyze_runs.py` size line | before 5,994 chars; after recorded |

Record both run ids, the tables, the size and the one-run-per-side noise caveat in
`specs/009-text-value-matching/results.md`. Report each criterion as met or not met, as 008
did.

## 4. Optional: web UI spot check

```bash
python -m web_ui.cli --port 8001    # vLLM holds 8000
```

Ask "Quanto foi pago pela AEB em 2012?". The trace should show either a matching filter or a
0-row result with `value_suggestions`, followed by a retry with "Agência Espacial Brasileira".
