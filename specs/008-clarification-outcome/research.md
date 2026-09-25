# Research: Clarification Outcome, Prompt v2 and Outcome-Based Grading

**Feature**: `008-clarification-outcome` | **Date**: 2026-09-24 | **Spec**: [spec.md](./spec.md)

The Technical Context had no open NEEDS CLARIFICATION items after the spec's clarification
session. This file records the design decisions that the spec leaves to the plan, the
alternatives rejected, and the risks the live acceptance runs (SC-001–SC-005) have to face.

---

## §1 One shared `Outcome` type

**Decision**: Define `Outcome = Literal["full", "partial", "none", "needs_clarification"]` once
in `qa_agent/models.py`. Use it for `AgentAnswer.outcome`, `QuestionAnsweringResult.outcome`,
`AgentRunLogEntry.outcome`, `_clamp_outcome`/`_finalize` in `qa_agent/capabilities.py`, and
in `testset_runner/models.py` (`Question.expected_outcome`, `QuestionResult.agent_outcome`,
`QuestionResult.expected_outcome`).

**Rationale**: Today the literal is written out five times. A fourth value (FR-001/FR-002)
would mean five edits that must stay in sync. One alias makes a missed spot a pyright error.
`testset_runner` already imports from `qa_agent.models` (`FailureDetail`, `RetrievalStep`), so
this adds no new dependency direction.

**Backward compatibility (FR-003, SC-006)**: widening a `Literal` only accepts more values.
Every stored run file and JSONL log line holds one of the three old values and still
validates. No migration is needed.

**Alternatives rejected**: a `StrEnum`. It serializes the same way, but it changes the
Python-side type for every existing caller and test that passes a plain string, and it adds
nothing that the `Literal` doesn't already give.

---

## §2 Clamp exemption (FR-004)

**Decision**: `_clamp_outcome` returns `reported` unchanged when
`reported == "needs_clarification"`. Otherwise, as today, it returns `"none"` when
`budget.successes == 0`.

**Rationale**: A clarifying question is usually asked *before* any query (US1 AC3), so the
zero-successes downgrade would always erase it. The downgrade exists to stop "full"/"partial"
claims that aren't backed by data. A clarifying answer makes no data claim, so exempting it
doesn't weaken grounding. The grader's amount check (§6) is what catches a clarifying answer
that leaks values.

**Alternatives rejected**: downgrading `needs_clarification` to `none` when there are no
successes. It contradicts US1 AC3 and would make #49 fail under v2 by construction.

---

## §3 Prompt versions: files, selection, validation

**Decision**:

- `src/qa_agent/prompts/system_v2.md` is a new file. `system_v1.md` is not touched
  (FR-005). A byte-level test pins v1's SHA-256.
- `prompt_loader` gains:
  - `DEFAULT_PROMPT_VERSION = "v2"`
  - `available_versions() -> list[str]`: the sorted `vN` names discovered from
    `prompts/system_*.md`
  - `check_version(version) -> None`: raises `UnknownPromptVersionError` naming the version and
    listing the available ones
  - `render(briefing, version=DEFAULT_PROMPT_VERSION) -> str`
- `UnknownPromptVersionError(ValueError)` lives in a new `qa_agent/exceptions.py`.
- `AgentSettings.prompt_version: str = DEFAULT_PROMPT_VERSION` (env
  `QA_AGENT_PROMPT_VERSION`), with a `field_validator` that calls `check_version`.
- `QaAgentQuestionAnswerer(..., prompt_version: str | None = None)` calls `check_version`
  **before** it builds anything when a version is given, and exposes
  `prompt_version` (the resolved `settings.prompt_version`) as a read-only property.
- `answer_question` renders with `settings.prompt_version`.

**Rationale**:

- Discovering versions from files means adding `system_v3.md` later needs no code change
  (Principle V, Eng. 2). It is also the only way the list in the FR-009 error message can
  stay correct.
- The explicit `check_version` call in the answerer gives the CLIs a clean, typed exception
  to catch *before any question is asked* (FR-009). The settings validator is a backstop, so
  the harness (`AgentSettings()` from env) can't start with a bad version either.
- The runner CLI records the version from `answerer.prompt_version`, not from the flag. When
  no flag is given, the version comes from pydantic-settings (env, then default). Reading it
  back from the built settings means the recorded value is always the one actually used
  (Principle I, Eng. 7).
- The default is v2 in every entry point (Clarification 1), because all of them go through
  `AgentSettings`.

**Alternatives rejected**:

- A hard-coded `Literal["v1", "v2"]` on the setting. Every new version would need a code
  edit, and the type and the files could drift apart.
- Validating only in the CLI. The harness and web UI would then fail late, on the first
  question.

---

## §4 Where the prompt version is recorded on a run

**Decision**: `TargetConfiguration.prompt_version: str | None = None`. The runner CLI builds
the answerer first, then builds `TargetConfiguration(model_name, base_url,
prompt_version=answerer.prompt_version)`. Runs stored before this feature load with `None`,
which is reported as "not recorded" (US4 AC4).

**Rationale**: `TargetConfiguration` is already "what this run was configured to use". It is
stored on `TestRun`, shown by `compare`, and never holds a credential. The prompt version is
the same kind of configuration as the model name. `RunComparison.run_a/run_b` already carry
the target, so `compare` shows the version with no new comparison field (FR-011).

**Alternatives rejected**:

- A new top-level `TestRun.prompt_version`. It would sit next to `target` and duplicate its
  role.
- Returning the version on every `QuestionAnsweringResult`. It is fixed for the whole run,
  so repeating it per answer adds noise and no information.

---

## §5 Briefing fingerprint

**Decision**:

- `prompt_loader.fingerprint(text) -> str` returns `sha256(text.encode("utf-8")).hexdigest()`.
- `QuestionAnsweringResult.briefing_fingerprint: str | None = None` is set by
  `_answer_with_selection` from `selection.briefing`, including when the agent run itself
  fails (the briefing was still used). It is `None` when dataset selection fails.
- The runner derives `TestRun.briefing_fingerprints: list[str] | None`: the **sorted distinct**
  non-`None` fingerprints across all results. Stored runs from before this feature load with
  `None` ("not recorded").
- `RunComparison` gains `briefing_fingerprints_a/_b` and `briefing_fingerprints_differ: bool`
  (list inequality). This is information only; transitions are unchanged (FR-011).

**Rationale**:

- The runner doesn't know the dataset before a question is asked (selection happens per
  question inside `answer_question`). So the fingerprint must come back with the answer,
  which also makes it a record of what was *actually* used.
- Normally the list has exactly one element (FR-010: same text gives the same fingerprint;
  changed text gives a different one). A list rather than a single string stays truthful if
  a run ever touches two briefings, because of a second dataset or a mid-run edit, and it
  needs no conflict rule. The CLI prints the single fingerprint in the normal case.
- SHA-256 hex matches `Testset.content_hash` (`testset_runner/loader.py`), so identity works
  the same way across the project.
- This is how the in-place briefing edit is justified against Eng. Principle 8
  (Clarification 3). See Complexity Tracking in plan.md.

**Alternatives rejected**:

- Hashing the whole rendered prompt. It mixes prompt and briefing identity. The version
  already identifies the prompt, and the spec asks for the briefing specifically.
- A per-question fingerprint on `QuestionResult`. The run-level list answers FR-010, and a
  per-question copy would repeat the same 64 characters 50 times.
- Reading the briefing file in the runner to hash it. That would duplicate dataset
  selection in `testset_runner` and could hash a different file from the one the agent
  used.

---

## §6 Outcome-aware grading rules

**Decision**: `DeterministicMatcher.grade` gains two keyword-only parameters,
`expected_outcome: Outcome | None = None` and `agent_outcome: Outcome | None = None`. The rules,
in order:

1. `expected_outcome is None` → `strategy.evaluate(expected, answer)`, exactly as today
   (FR-016, SC-007).
2. `agent_outcome != expected_outcome` → `not_matched` (FR-013).
3. `expected_outcome in {"none", "needs_clarification"}` → `not_matched` if
   `contains_amount(answer)`, otherwise `matched`. The `expected` text is not used here
   (FR-014).
4. Otherwise (`full`/`partial`) → `strategy.evaluate(expected, answer)` (FR-015).

"Errored" stays decided in the runner, before grading, as today (FR-017). The runner passes
`question.expected_outcome` and `answer_result.outcome`, and stores `expected_outcome` on
`QuestionResult` (FR-018).

**`contains_amount`** is a module-level function in `matcher.py` built on three regular
expressions (Clarification 2):

| Pattern | Catches | Example |
|---|---|---|
| `R\$\s*-?\d` | any number after `R$` | `R$ 42`, `R$42.750,00` |
| `\d[.,]\d` | a digit, a `.` or `,`, then a digit (decimal or thousands separator) | `1.234`, `12,5`, `206.805.295` |
| `\d\s*%` | a number followed by `%` | `36%`, `12,5 %` |

The following are **not** caught, by design:

- `2005`, `2005.` or `2005,` at the end of a sentence: no digit follows the separator
- `1.` or `2)` list markers
- `Amazônia-1`
- `2008 a 2012`

**Known imprecision (accepted and documented in the docstring)**:

- `2005,2006` with no space would be flagged.
- A small count written as a plain integer is not caught (spec Edge Cases).
- The rule works on text only and never looks at the dataset (Principle VI).

**Rationale**:

- Keeping the existing `MatchStrategy` protocol unchanged means custom strategies and every
  existing caller keep working.
- The outcome gate wraps the strategy instead of replacing it.
- Pure functions with no `pydantic-ai` import satisfy FR-020 and Eng. 6.

**Alternatives rejected**:

- A new `MatchStrategy.evaluate` signature. It would break the protocol for every
  implementation.
- An `OutcomeMatchStrategy` chosen per record. It needs dispatch and gives nothing over four
  ordered `if`s.
- Reusing `_NUMERIC_SUBSTRING` with "any number fails". Clarification 2 explicitly rejected
  that, because it fails on years and "Amazônia-1".

---

## §7 Testset edit (FR-019)

**Decision**: Add `"expected_outcome"` to #48 (`"none"`), #49 (`"needs_clarification"`) and
#50 (`"none"`) in `data/testsets/orcamentos-aeb-csv.json`. The edit keeps the file's existing
2-space indentation and key order: the new key goes after `"source"`. No other byte changes.
`Question.expected_outcome: Outcome | None = None`. An invalid value makes
`_QUESTIONS_ADAPTER.validate_python` raise, which already maps to `TestsetLoadError` with the
record's index in the pydantic message (FR-012).

`data/testsets/orcamentos-aeb-csv-10.json` is not touched (it doesn't contain #48–#50).

**Consequence**: the testset `content_hash` changes. So runs made before the edit, including
`20260924T121028315459Z`, can't be `compare`d against new runs (spec Edge Cases). SC-004 uses
a fresh v1 run and a fresh v2 run.

---

## §8 Briefing wording guidance (FR-007) and the SC-003/SC-004 risk

**Decision**: Add a section "Qual medida a pergunta pede" to
`data/briefings/orcamentos-aeb-csv.md` with this content:

- **Wording that selects a measure**:
  - "gasto", "gastou", "pago", "pagamento", "desembolso" → `pago`
  - "orçamento previsto", "dotação", "autorizado" → `dotacao_atual`
  - "empenhado", "empenho" → `empenhado`
  - "liquidado", "liquidação" → `liquidado`
- **Ambiguous**: "orçamento", "valor do orçamento" or "recursos" with no qualifier, when
  asking for an amount. The four measures can differ a lot (e.g. up to ~36% for the AEB in
  2005). The briefing gives no instruction for this case: *what to do* with ambiguity belongs
  to the prompt (v1: pick and declare; v2: ask). The briefing only states *what* is
  ambiguous.
- **Counting questions are not a choice of measure**: "quantas ações tiveram
  execução/gastos em ANO" counts the records present for that year. Each record is an action
  with budget registered in the year, including those with `pago = 0`.
- Fix the existing synonyms table so it doesn't contradict the section: "gasto empenhado"
  stays under `empenhado` because it is qualified, and bare "gasto" is covered by the new
  section.

**Risk found while planning (evidence from run `20260924T121028315459Z`)**:

- #28 ("Quantas ações orçamentárias tiveram execução em 2006?", expected 31) and #29
  ("… tiveram gastos em 2008?", expected 31) matched under v1 by counting records. In 2008
  there are 31 records but only 27 with `pago > 0`.
- If v2 plus a naive "gasto → pago" rule made the agent count `pago > 0`, #29 would regress
  (SC-004). Asking for clarification there would fail SC-003.
- The counting bullet above exists to prevent this. It states how this dataset defines
  "an action with execution in a year". It is not a testset-specific hint, and it matches
  what v1 already did.
- #37 (years with execution for Pnae) was not_matched under v1 and is not a regression risk.

**Rationale**:

- Principle V: which word means which column is knowledge about this dataset, so it goes in
  the briefing.
- The prompt only carries the general rule "ask when readings differ".
- Keeping the briefing neutral about what to do with ambiguity is what keeps the SC-002 v1
  baseline meaningful (spec Assumptions: the briefing "doesn't override v1's pick-a-reading
  rule").

**Alternatives rejected**:

- Putting the wording table in `system_v2.md`. That violates Principle V.
- A separate `orcamentos-aeb-csv-v2` briefing. Clarification 3 chose to edit in place and
  record a fingerprint.

---

## §9 Prompt v2 content outline

**Decision**: `system_v2.md` starts as a copy of v1, with these changes (full rule list in
[contracts/prompt-v2.md](./contracts/prompt-v2.md)):

- **Rule 4** (ambiguity): replaced. Ask a clarifying question in Portuguese, listing the
  possible readings in plain language, with no values. Answer directly when the wording
  already names the measure (as the dataset description explains), or when all readings give
  the same amount. In that case, say that they agree.
- **Rule 5** (coverage): gains "never give the value of a similar or related item as a
  substitute. If nothing matches, report `none`". It also says that when the question is not
  covered at all (e.g. a year outside the range), report `none`, even if it is also
  ambiguous.
- **Rule 8** (classification): replaced. The outcome goes only in the `outcome` field, never
  in the answer text. The field now has four values with definitions, including
  `needs_clarification`.
- Rules 1–3, 6 and 7 are copied word for word (FR-006: carry over the other v1 rules).
- The `{briefing}` placeholder is kept, so `render` stays `template.format(briefing=...)`.

**Rationale**: Each change maps to one observed failure. Rule 4 → #49. Rule 5 → #48 (the
substitute) and the edge case "ambiguous and not covered". Rule 8 → #48/#50 labels and the
"Classificação: partial." leak. Nothing else changes, so v1→v2 differences in the SC-004
comparison can be attributed to these rules (Principle II).

---

## §10 CLI surface

**Decision**:

- **`testset_runner run`**: new `--prompt-version` flag, with fallback env
  `QA_AGENT_PROMPT_VERSION`, then default v2 via settings. The CLI catches
  `UnknownPromptVersionError` when it builds the answerer, prints
  `Error: unknown prompt version 'v9' (available: v1, v2).` and exits 1 before loading the
  testset or asking anything. After a run it also prints `Prompt version: v2` and
  `Briefing fingerprint: <first 12 hex chars>`, or "not recorded".
- **`testset_runner compare`**: prints each run's prompt version and briefing fingerprint,
  and a line `Briefing fingerprints differ: yes/no`.
- **`web_ui`**: new `--prompt-version` flag with the same env fallback. It catches
  `UnknownPromptVersionError` and exits 1 before binding the port.
- **Harness**: gets the version from `AgentSettings()` (env). It already records
  `settings.model_dump()`, which now includes `prompt_version`.

**Rationale**: This matches the existing flag → `QA_AGENT_*` env → default pattern in both
CLIs (research 004 §9, 005 R5). Adding the flag to the web UI costs one line and keeps the
two CLIs symmetric, which FR-008 ("every entry point") implies.

---

## §11 Measuring SC-001–SC-008

**Decision**: Measure with two fresh full runs on the edited testset and the configured
model (the `gpt-5.4-nano` target of the evidence run): one with `--prompt-version v1`, one
with the default (v2). Then `compare v1 v2`. One run each, strict (Clarification 4). No
re-runs. The measurements are:

- **SC-001/SC-002**: the `match_status` of #48–#50 in each run.
- **SC-003**: the count of `agent_outcome == "needs_clarification"` excluding #49.
- **SC-004**: `newly_failing == 0` in the comparison (A = v1, B = v2).
- **SC-005**: a scan of v2 `actual_answer`s for the label pattern
  `\b(full|partial|none|needs_clarification)\b|Classifica[çc][ãa]o\s*:` (case-insensitive,
  checked by hand if it hits Portuguese words). This is a quickstart check, not a grading
  rule.
- **SC-006**: loading every file in `data/testset_runs/` and every line of the JSONL logs
  with the new models. `data/testset_runs/` and `data/logs/` are gitignored, so this is a
  local quickstart check. CI covers it with a unit test that loads the committed
  `tests/fixtures/testset_runner/pre-006-run.json`, plus a new committed fixture: a trimmed
  copy of run `20260924T121028315459Z` with a few results, including #48–#50.
- **SC-007**: two checks.
  - CI: a unit test regrades every result in the committed fixtures with
    `expected_outcome=None` and asserts the stored `match_status`.
  - Local (quickstart): the same check over every result in the full run file.
- **SC-008**: the `needs_review` count of the v2 run compared with 16.

The results are written to `specs/008-clarification-outcome/results.md` (as in feature 006),
with run IDs, per Principle I and the Development Workflow rule on accuracy claims.

**If acceptance fails**: change the prompt v2 text or the briefing, then do a new pair of
runs (spec Assumptions). Never change the grader to make a run pass.
