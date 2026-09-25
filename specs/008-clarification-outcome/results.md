# Results: Clarification Outcome, Prompt v2 and Outcome-Based Grading (008)

Evidence for SC-001–SC-008 (Principles I–II). See quickstart.md §1–§4.

**Verdict: acceptance FAILS.** SC-001, SC-002 and SC-004 fail on the one strict pair of
runs (Clarification 4). SC-003, SC-005, SC-006, SC-007 and SC-008 pass. Per tasks.md T052,
the fix is a change to `system_v2.md` or the briefing, followed by a new pair of runs.
The grader is not changed.

## Setup

- **Code**: working tree on top of commit `4a09a69` (feature 008 uncommitted at run time).
- **Model**: `gpt-5.4-nano`, base URL `https://api.openai.com/v1`.
- **Retry policy**: max_attempts=3, waits 2.0 s ×2.0 (cap 60.0 s). No question was
  retried, and none errored in either run.
- **Testset**: `data/testsets/orcamentos-aeb-csv.json` with `expected_outcome` on #48–#50.
- **Briefing fingerprint**: `4f2597d6ed81…` (the same in both runs; `compare` prints
  "Briefing fingerprints differ: no").

| Run | Prompt version | Run ID | Match rate | Status counts |
|-----|----------------|--------|------------|---------------|
| V1 | v1 (`--prompt-version v1`) | `20260925T001355609469Z` | 68.0% | matched 34, not_matched 3, needs_review 13 |
| V2 | v2 (default) | `20260925T002913072725Z` | 66.0% | matched 33, not_matched 4, needs_review 13 |

By category (V1 → V2): calculation 70.6% → 76.5%, edge-cases 66.7% → 66.7%,
multiple-files 0.0% → 0.0%, single-lookup 100.0% → 90.0%.

## `compare V1 V2`

```text
Run A: model=gpt-5.4-nano base_url=https://api.openai.com/v1 prompt_version=v1
  retry policy: max_attempts=3, waits 2.0s x2.0 (cap 60.0s)
  briefing fingerprint: 4f2597d6ed81
Run B: model=gpt-5.4-nano base_url=https://api.openai.com/v1 prompt_version=v2
  retry policy: max_attempts=3, waits 2.0s x2.0 (cap 60.0s)
  briefing fingerprint: 4f2597d6ed81
Briefing fingerprints differ: no

  newly_failing: 2
  newly_passing: 1
  still_failing: 2
  still_passing: 32
  unchanged_other: 13

  [newly_failing] n=5: Quanto foi pago em pensões para servidores civis em 2001?
  [newly_failing] n=6: Quanto foi gasto com pagamento de aposentadorias e pensões de servidores civis em 2002?
  [newly_passing] n=35: Quanto foi gasto (pago) com a previdência de inativos e pensionistas da União entre 2010 e 2015?
```

## Success criteria

| Criterion | Measured | Pass when | Result |
|-----------|----------|-----------|--------|
| SC-001 | V2: #48 `none`/matched, #49 `full`/not_matched, #50 `none`/matched | 3 of 3 matched, #49 a question | **FAIL** (2 of 3) |
| SC-002 | V1: #48 `none`/matched, #49 `full`/not_matched, #50 `none`/matched | 3 of 3 not_matched | **FAIL** (1 of 3) |
| SC-003 | V2 results with `needs_clarification` besides #49: none | 0 | PASS |
| SC-004 | `newly_failing` = 2 (#5, #6) | 0 | **FAIL** |
| SC-005 | V2 label hits (quickstart helper): none | 0 | PASS |
| SC-006 | Both pre-008 run files and all 204 lines of `qa_agent_runs.jsonl` load (T051); committed fixtures load (tests) | 100% | PASS |
| SC-007 | Regrade diffs: `[]` for both local pre-008 runs (T051) and for `008-sample-run.json` (test) | 100% same | PASS |
| SC-008 | V2 needs_review = 13, vs 16 in `20260924T121028315459Z`; #48–#50 are no longer needs_review | ≤ 13 | PASS |

V1 also had one label hit (#35), which is allowed since SC-005 checks only V2.

## Why the failing criteria fail

### SC-001: #49 under v2 did not ask

V2 answer: "Em 2005, o valor do orçamento (dotação atual) da Agência Espacial Brasileira
(AEB) foi de R$ 206.805.295,00. As leituras (dotação atual) para “orçamento” coincidem
neste dataset." Outcome `full`.

The trace shows one `aggregate_rows` call on `dotacao_atual` only. The agent never
computed the other readings, yet claimed they "coincide". In fact they don't: paid is
R$ 131.995.537. The model used rule 4's last clause ("se todas as leituras levarem ao
mesmo valor, responda diretamente e diga que as leituras coincidem") as a way out, without
checking it. Candidate fix in `system_v2.md` rule 4: require that the agreement be
established by queries of every reading, or drop the clause.

### SC-002: v1 already handled #48 and #50

V1 reported `none` for both with no amount. That is correct under the new grading, so they
graded `matched`. In the evidence run `20260924T121028315459Z` the same model reported
`partial` for both. The baseline behavior varies between runs. SC-002 assumed v1 fails all
three, and no change to v2 or the briefing can fix a v1 run. Note that V1's #48 answer
also states something false ("não há registros … para a Agência Espacial Brasileira no ano
de 2005"). The outcome grader doesn't catch that, because it checks outcome and amounts,
not the claim.

This needs a decision on the criterion itself (e.g. judge SC-002 on #49 only, or on
the evidence run), not a prompt change.

### SC-004: #5 and #6 regress

Both regressions follow the same pattern. The action names are "Pagamento de Pensões a
Servidores Civis" and "Pagamento de Aposentadorias e Pensões - Servidores Civis". The
agent searched `nome_acao contains "pensão"` (singular). That substring doesn't occur in
"Pensões", so it got 0 rows, did not try another spelling, and reported `none` (#5) or
`partial` (#6). Under v1 the same model found the rows.

The likely cause is v2 rule 5's new "se nada na base de dados corresponder … classifique
como none", which makes one empty search look like a finished answer. Candidate fix in
`system_v2.md` rule 5: before concluding that nothing matches, retry with other forms of
the terms (singular/plural, a shorter stem such as "pens"), or list the candidate names. The
variance seen in SC-002 also means a single run can't separate prompt effect from noise,
but Clarification 4 makes this run the one that counts.

### Newly passing

#35 under v2 found the program "PREVIDÊNCIA DE INATIVOS E PENSIONISTAS DA UNIÃO" and
matched the expected 1.148.602. Under v1 it gave a partial answer with a different total.

## Deterministic checks (T049–T051)

- `pytest tests/contract tests/unit`: 423 passed. `pyright src/`: 0 errors.
  `git diff --stat src/qa_agent/prompts/system_v1.md`: empty.
- `--prompt-version v9` (runner CLI, web UI CLI, and `QA_AGENT_PROMPT_VERSION=v9`):
  `Error: unknown prompt version 'v9' (available: v1, v2).`, exit 1, no run file written.
- Quickstart §4 on local data:

  ```text
  data/testset_runs/20260921T103437122660Z.json prompt_version: not recorded regrade diffs: []
  data/testset_runs/20260924T121028315459Z.json prompt_version: not recorded regrade diffs: []
  log lines validated: 204
  ok
  ```
