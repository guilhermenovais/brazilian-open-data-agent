# Results: Forgiving Text Matching and Value Suggestions (009)

Live evaluation (T028–T033), 2026-09-25.

- **Target**: `Qwen/Qwen3-8B-AWQ` at `http://localhost:8000/v1` (local vLLM), the 008 evidence target
- **Prompts**: unchanged. `system_v2.md` for the conversation path, `system_v1.md` for the
  standalone path (research.md R7). `git diff main -- src/qa_agent/prompts` is empty.
- **Retry policy**: `max_attempts=3, waits 2.0s x2.0 (cap 60.0s)`; history limit 16000
- **Text matching** (recorded on both after runs): `value_list_threshold=30, max_suggestions=5, stopwords=pt_v1`
- **Only difference** between before and after: the data tools' behavior and descriptions.

| Run id | What | Baseline (008) |
|---|---|---|
| `20260925T120757914345Z` | conversation test set `orcamentos-aeb-csv-conversations.json` (19 conversations, 56 turns, 18 scored), same content hash `7319d588…` | `20260925T095751382002Z` |
| `20260925T124606848510Z` | standalone `orcamentos-aeb-csv-10.json`, same content hash `178ba052…` | `20260925T100203429266Z` |

Every number below comes from these run files through
`specs/009-text-value-matching/analyze_runs.py` or `testset_runner compare`.

> **Noise caveat**: each side is a single run. Small categories move by a whole
> conversation on one sampling difference. The 3 `follow-up-metric` conversations, the 3
> `follow-up-reference` ones and the 1-conversation categories cannot separate a real
> effect from run-to-run variation. Read per-category changes as indications, not
> measurements.

## Outcome per success criterion

| SC | Target | Measured | Met? |
|---|---|---|---|
| SC-001 forgiving matching | 100% of case/accent/hyphen/punctuation/whitespace variants match, with `equals` and `contains`; stopwords don't matter for `contains` | `tests/unit/data_access/test_text_matching.py` and `tests/contract/data_access/test_text_matching_filters.py` (fixture `budget_actions.csv`), through both `query_rows` and `aggregate_rows` | Yes |
| SC-002 008 failing values | each matches, or the intended value is in the top 3 suggestions | "AEB" → 0 rows, #1 "Agência Espacial Brasileira" (overlap 1, 301 rows); "desenvolvimento do satélite Amazônia-1" → matches 5 rows directly; "CBERS-3" → 0 rows, #1 "Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS-3" (overlap 2); "satélite CBERS 3" (`contains`) → matches 5 rows | Yes |
| SC-003 value lists | 100% of each low-cardinality field's values listed | `nome_unidade` 2/2, `nome_programa` 13/13, `data_ano` 20/20; `nome_acao` (116), `id_orcamento` (438) and the four money fields (355–408) not listed | Yes |
| SC-004 (a) follow-up-metric | ≥ 2/3 (from 0/3) | **3/3** | Yes |
| SC-004 (b) no failure from a 0-row text filter whose value exists | 0 such scored turns | **1**: `follow-up-reference-01` t2 (see below) | **No** |
| SC-005 standalone | 0 `newly_failing` | `compare`: 6 still passing, **1 newly failing** (n=1), 3 unchanged_other | **No** |
| SC-006 existing tests | pass unedited | `test_query.py`, `test_aggregation.py`, `test_query_engine.py` pass with no diff against `main`; `test_inspection.py` only gained cases; 530 offline tests pass, pyright clean | Yes |
| FR-019 `inspect_schema` size | recorded | `dados_gerais/tb_geral.csv`: **5,994 → 7,186 characters (+1,192, +20%)** | Recorded |

**Summary**: every mechanism-level criterion (SC-001, SC-002, SC-003, SC-006) is met. On the
conversation set, scored turns went from **10/18 (55.6%) to 14/18 (77.8%)**, and
`follow-up-metric` went from 0/3 to 3/3. SC-004 (b) is not met because of one turn. In that
turn the model ANDed three `equals` conditions on the same field. Each value exists, so the
combination is empty by construction, and the model declined instead of splitting the query. SC-005 is not met because of one standalone question (n=1) that fails the same way. In
both regressions the model got `"value_suggestions": []` after ANDing conditions that
cannot hold together, and then declined. With one run per side this may be noise. But the
two regressions share this pattern, and it points at the follow-up described below.

## Mechanism check on the real dataset (quickstart §2, T028)

```text
AEB 0 [{'field': 'nome_unidade', 'op': 'equals', 'value': 'AEB', 'candidates': [{'value': 'Agência Espacial Brasileira', 'overlap': 1, 'row_count': 301}]}]
desenvolvimento do satélite Amazônia-1 5 None
satélite CBERS 3 5 None
id_orcamento 438 None
data_ano 20 ['2000', …, '2019']
nome_unidade 2 ['Agência Espacial Brasileira', 'Ministério da Ciência, Tecnologia, Inovações e Comunicações']
nome_programa 13 ['Apoio Administrativo', …, 'Valorização do Servidor Público']
nome_acao 116 None
dotacao_atual 355 None
empenhado 408 None
liquidado 399 None
pago 400 None
```

## Conversation run: per category (scored turns matched / scored)

| Category | Before `…095751…` | After `…120757…` |
|---|---|---|
| clarification | 2/3 | 3/3 |
| clarification-ignored | 1/1 | 1/1 |
| clarification-insufficient | 0/1 | 0/1 |
| follow-up-metric | 0/3 | **3/3** |
| follow-up-reference | 2/3 | 2/3 |
| follow-up-year | 3/3 | 3/3 |
| fresh-chat-follow-up | 0/2 | 0/2 |
| long-conversation | 0/0 | 0/0 |
| standalone-after-unrelated | 2/2 | 2/2 |
| **Total** | **10/18 (55.6%)** | **14/18 (77.8%)** |

Status counts after: 14 matched, 4 not_matched, 1 errored (unscored turn), 37 unscored.

### Per-turn transitions (scored turns)

`matched → matched` 9, `not_matched → matched` 5, `matched → not_matched` 1,
`not_matched → not_matched` 3.

| Conversation | Turn | Category | Transition | Cause (from the turn's `steps`) |
|---|---|---|---|---|
| follow-up-metric-01 | 2 | follow-up-metric | not_matched → matched | `aggregate_rows` `equals "AEB"` → 0 groups + suggestion → retried with "Agência Espacial Brasileira" → answered |
| follow-up-metric-02 | 2 | follow-up-metric | not_matched → matched | called `inspect_schema` first (the `nome_unidade` value list), then filtered on "Agência Espacial Brasileira" directly: no empty result at all |
| follow-up-metric-03 | 2 | follow-up-metric | not_matched → matched | the same `equals "desenvolvimento do satélite Amazônia-1"` that returned 0 rows in 008 now matches (normalization alone) |
| follow-up-reference-02 | 2 | follow-up-reference | not_matched → matched | `equals "CBERS-3"` → 0 groups + 4 suggestions; the model did not copy a suggestion but switched to `contains "CBERS-3"`, which matches the CBERS-3 action (word-start rule), and answered |
| clarification-03 | 2 | clarification | not_matched → matched | not a text-filter case: in 008 the model summed `query_rows` rows by hand and got it wrong; this time it used `aggregate_rows` with the full unit name. Counted as run-to-run variation, not as an effect of this feature. |
| follow-up-reference-01 | 2 | follow-up-reference | matched → not_matched | see below |

### The regression: `follow-up-reference-01` turn 2

"Qual dessas teve o menor valor empenhado, e quanto foi?" (expected 25404101). In both runs
the model's first call ANDs three `nome_acao` conditions, one per action named in the
previous turn. No single row can hold three different action names, so the result is
always empty:

- **Before**: the empty results had no explanation. The model tried again with narrower
  filters until it queried one action at a time, and got the answer right.
- **After**: the first call used `equals "Agência Espacial Brasileira (AEB)"` and got a
  suggestion. The second call fixed the unit and returned `"value_suggestions": []`, which
  means each condition matches rows on its own and only their combination is empty. The
  model did not read it that way. It declined ("os nomes das ações podem ser diferentes")
  after two steps.

The matcher and the suggestions behaved as specified. The cause is the model's AND over
alternatives of one field, and an empty suggestion list that does not say *why* the
result is empty. See the follow-up under "Standalone run": the standalone regression has the same shape.

### Errored turn

`long-conversation-01` t1 (unscored): the model emitted a raw `<tool_call>` text block
instead of the structured output (`ValidationError … json_invalid`). This model output
failure is unrelated to the data tools. The rest of the conversation ran normally.

## Zero-row audit (after run, `analyze_runs.py` §2)

- Every empty `query_rows`/`aggregate_rows` result with a text condition that matched
  nothing on its own carried `value_suggestions`. Every "AEB" miss listed "Agência Espacial
  Brasileira", and "CBERS-3" listed 4 CBERS actions with the intended one first.
- "Next step used one" (the next step's arguments contain a suggested value) was **yes** in
  the scored turns that turned into matches (`follow-up-metric-01` t2, `follow-up-year-02`
  t2) and in several context turns. It was **no** in most `long-conversation-01` turns:
  there the model did not retry the filter. It moved to another call shape, such as
  `aggregate_rows` with the full name or a query without the unit, or it answered. Those
  turns are unscored.
- The audit prints one line per text condition of an empty step. The "Suggested values"
  column counts the step's suggested values, so an unrelated condition on the same step
  (e.g. `data_ano equals '2012'`) shows the same count.
- SC-004 (b) count: **1** (`follow-up-reference-01` t2, above).

## Standalone run and `compare` (SC-005)

Report (`run`, T031):

```text
Run 20260925T124606848510Z: 10 questions
Match rate: 60.0%
By category:
  calculation: 100.0% (3 questions)
  edge-cases: 0.0% (1 questions)
  multiple-files: 0.0% (2 questions)
  single-lookup: 75.0% (4 questions)
Retry policy: max_attempts=3, waits 2.0s x2.0 (cap 60.0s)
Text matching: value_list_threshold=30, max_suggestions=5, stopwords=pt_v1
Questions retried: 0
Errored after exhausting retries: 0
```

`python -m testset_runner.cli compare data/testset_runs/20260925T100203429266Z.json data/testset_runs/20260925T124606848510Z.json`:

```text
  newly_failing: 1
  still_passing: 6
  unchanged_other: 3

  [newly_failing] n=1: Quanto foi pago aos dependentes dos servidores para assistência pré-escolar em 2000?
```

**n=1 (expected 8351)**:

- **Before**: one call, `nome_acao contains "assistência pré-escolar"` + `data_ano equals
  2000`. It matched "Assistência Pré-escolar aos Dependentes dos Servidores e Empregados"
  and the answer was correct.
- **After**: the model added a third condition, `nome_programa contains "assistência"`. The
  row's program is "Atenção À Criança", so the combination is empty. The response was
  `"value_suggestions": []`, because each condition matches rows on its own (e.g. the
  program "Assistência ao Trabalhador"). The model declined after that single call.

The extra condition would also return 0 rows under the pre-009 substring rule. So the
regression comes from the model choosing a different first call, not from a matching
change. The feature did not help it recover either: an empty suggestion list does not say
that the conditions exist separately but not together.

**Follow-up (not part of this feature)**: in both regressions (this one and
`follow-up-reference-01` t2), the model declined right after `value_suggestions: []`.
Candidate change, to be measured with its own before/after: have the `query_rows` and
`aggregate_rows` descriptions state that `[]` means "each filter matches rows on its own,
but not together: drop or loosen one filter". Alternatively, attach to the empty result
the row count of each text condition alone.

## Other observations

- Turns with ungrounded figures (reported by the grounding screen, not scored): 17 before,
  22 after. More turns now reach a real answer instead of declining, and each such answer
  has figures to screen. This feature adds no figure computation of its own. The per-turn
  verdicts were not reviewed by hand for this feature.
- `inspect_schema` grows by 1,192 characters on the evaluated source. That is well inside
  the context budget, and no value-list cap was needed (Clarifications Q4).

## Optional web UI spot check (T035)

Not run. The conversation run already exercises the same "Quanto foi pago pela AEB …"
path (`follow-up-metric-01` t1: 0 rows + suggestion → retry with "Agência Espacial
Brasileira").
