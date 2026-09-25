# Research: Forgiving Text Matching and Value Suggestions

Phase 0 output for [plan.md](./plan.md). The Technical Context has no open
`NEEDS CLARIFICATION` items. The spec clarifications fixed the matching rule (word-start
prefixes), the prompt policy (tool descriptions only), the evaluation size (one run per test
set) and the value-list limit (threshold only). The decisions below settle how each
requirement is built.

A prototype of R1–R4 was run against `dados_gerais/tb_geral.csv` while planning:

| Filter (field) | Result under the planned rules |
|---|---|
| `equals "desenvolvimento do satélite Amazônia-1"` (`nome_acao`) | matches "Desenvolvimento do Satélite Amazônia-1" directly: the 008 failure was a case-only mismatch (R1) |
| `equals "AEB"` (`nome_unidade`) | 0 rows; suggestion #1 "Agência Espacial Brasileira" (overlap 1, via acronym), no other candidate |
| `contains "satélite CBERS 5"` (`nome_acao`) | 0 rows; the two "…Projeto CBERS-3/4" values rank first (overlap 2) |
| `equals "MCTIC"` (`nome_unidade`) | 0 rows; suggestion #1 "Ministério da Ciência, Tecnologia, Inovações e Comunicações" (acronym "mctic") |

So SC-002 is reachable by mechanism alone.

## R1. Normalization: NFKD, drop combining marks, casefold, non-word → space

**Decision**: `normalize(text)` = `unicodedata.normalize("NFKD", text)`, drop every
character where `unicodedata.combining(c)` is non-zero, `casefold()`, replace each run of
`[\W_]` (Unicode-aware regex) with a space, then `" ".join(s.split())`. Words are
`normalize(text).split()`.

**Rationale**:
- Standard library only, no new dependency (Principle VII).
- NFKD splits "ã" into "a" + a combining tilde, so accents drop and the base letter stays.
  Compatibility decomposition also folds "º"/"ª" to "o"/"a", matching how people type them.
- `\W` is Unicode-aware in Python 3, so non-Latin letters and digits survive as word
  characters. Every symbol ("§", "%", "-", ",", "(") becomes a separator. The same function
  runs on both sides, so every value matches itself (spec edge case).
- `casefold()` rather than `lower()` handles "ß" → "ss" and similar on both sides.

**Alternatives considered**:
- *`unidecode`*: transliterates non-Latin scripts, which changes words instead of folding
  them, and adds a dependency. Rejected.
- *Only strip hyphens and a fixed punctuation set*: misses "(", "/", "§" and the like, which
  appear in real action names ("Satélite Sino-Brasileiro (CBERS)"). Rejected.

## R2. `equals`: whole normalized value; `contains`: every query word starts a stored word

**Decision**:
- `equals` matches when `normalize(stored) == normalize(value)`. No stopword removal
  (spec Assumptions).
- `contains` computes the query words: the normalized words of `value` minus stopwords, or
  all of them when that would leave none (FR-003). It matches when every query word is a
  prefix of at least one normalized word of the stored value, in any order. With no query
  words at all (value empty or only punctuation), it matches every non-missing value.
- Missing stored values (`None`, NaN, or empty/whitespace-only strings, the existing
  `_is_missing` rule) never match either operator.

Both masks are computed once per distinct stored value and mapped back onto the column
(`column.map(...)` over a dict built from `column.unique()`), so each distinct string is
normalized once per condition.

**Rationale**: This is the clarified rule (Clarifications Q1). A word-start prefix lets
"satel" match "Satélite" but keeps "4" from matching "2014" or "CBERS-14". "4" still matches
"CBERS-4A" because the hyphen splits it into "cbers" and "4a". The existing contract test
`contains "AL"` → only "Alice" still holds, because "al" starts "alice".

**Behavior change on missing values**: before this feature, `equals ""` matched empty cells
and `contains ""` matched every row. The spec edge cases state that missing values never
match, and `contains` with an empty value matches "every row with a value". This plan
follows the edge cases. US1-AS7 ("a value that already matched exactly matches the same
rows") holds for every non-missing value. This change is called out in the contract and
covered by a test, so it is not a silent side effect.

**Alternatives considered**:
- *Normalized substring for `contains`*: "cbers 4" would still match "cbers 14" and word
  order would still matter. Rejected by Clarifications Q1.
- *Vectorized pandas `.str` operations*: `.str.normalize` exists, but combining-mark
  stripping and prefix-of-any-word need Python per value anyway. The per-distinct-value map
  does the same work once per unique string, which is cheaper on these repetitive columns
  (438 rows, 2–116 distinct text values). Rejected as no simpler.

## R3. Stopwords: a named, versioned text file, selected by name in the config

**Decision**: `src/data_access/stopwords/pt_v1.txt`, one word per line, `#` comments
allowed. The config field `stopwords: str = "pt_v1"` names it. `load_stopwords(name)` reads
`stopwords/<name>.txt`, normalizes each word with R1 and returns a `frozenset[str]`
(cached per name). An unknown name fails when the config is validated, not at query time.

Contents of `pt_v1` (normalized form): articles (`a o as os um uma uns umas`),
prepositions and contractions (`de do da dos das em no na nos nas num numa dum duma ao aos
por pelo pela pelos pelas para pra com sem sob ate`, where "à"/"às" normalize into "a"/"as"),
conjunctions (`e ou nem mas que`).

**Rationale**: FR-004 and Principle V require the list to be data, not code. The file
pattern mirrors `qa_agent/prompts/system_<version>.md` (Eng. 8): a new list is a new file,
never an edit to `pt_v1`, and the recorded run configuration names the version it used
(R6). Another language is another file (spec Assumptions).

**Alternatives considered**:
- *NLTK/spaCy stopword lists*: a heavy dependency for ~40 words, and their Portuguese lists
  include content-bearing words ("estado", "nossa") that appear in real program names.
  Rejected.
- *List inside the dataset briefing*: stopwords are a property of the language, not of one
  dataset, and the data access layer does not read briefings. Rejected.

## R4. Suggestions: computed in the capability, ranked by word-start overlap plus acronym

**Decision**: In `data_access.capabilities.query_rows` and `aggregate_rows`, after the
result is known to be empty (0 matching rows, which is also the only way to get 0 groups):

1. For each `equals`/`contains` condition, run the engine on the **unfiltered** source with
   that condition alone. If it matches rows, skip the condition (US2-AS3/AS4).
2. Otherwise rank the condition field's distinct non-missing stored values:
   - candidate tokens = the value's normalized words + its acronym (first letter of each
     non-stopword word, e.g. "Agência Espacial Brasileira" → `aeb`);
   - `overlap` = number of query words (R2) that are a prefix of some candidate token;
   - keep values with `overlap ≥ 1`, sort by `overlap` desc, then row count desc, then raw
     value by code point asc, and keep the first `max_suggestions` (default 5).
3. Attach one `ValueSuggestion` per zero-match condition, with an empty `candidates` list
   when nothing overlaps (US2-AS5).

Range conditions never get suggestions (US2-AS7). A non-empty result never carries the
field (FR-013).

The ranking is a pure function in `data_access/text_matching.py`
(`rank_candidates(value_counts, value, rules, limit)`), so it can be tested without a
DataFrame. Row counts come from `df[field].value_counts()` on the source already in memory
(spec Assumptions: no second read).

**Rationale**:
- Using the same word-start rule for `contains` and for ranking means a suggested value
  always explains itself: the words the agent typed start words of the suggested value.
- The acronym is only a ranking token, never a match rule, so `equals "AEB"` never silently
  matches (spec Assumptions).
- Counting query words, not candidate words, keeps short values from being penalised and
  long values from winning just by being long.
- Checking each condition alone separates "value not found" (suggestions) from "no rows for
  this combination" (no suggestions), as US2-AS4 requires.

**Cost**: one extra engine pass per text condition, and only on empty results. The ranking
visits each distinct value once. On the evaluated source this is ≤ 116 values. For a field
with ~10⁶ distinct values it is a single Python loop of about a second, which is within a
model round-trip. No cap is added before a need is shown (Principle VII).

**Alternatives considered**:
- *Edit distance / `difflib.get_close_matches`*: cannot link "AEB" to "Agência Espacial
  Brasileira" and ranks by character similarity, which the spec does not ask for. Rejected.
- *Suggestions on every result*: adds tokens to successful calls and changes their shape
  (FR-013). Rejected.
- *Suggestions only for the whole combined filter*: cannot tell the agent which condition
  is wrong. Rejected (FR-012).

## R5. Value lists in `inspect_schema`: added to `FieldInfo`, counted on the whole source

**Decision**: `FieldInfo` gains `distinct_count: int` and `values: list[str] | None`.
`SchemaInspectionResult` gains `value_list_threshold: int`. For each observed field
(the existing rule, unchanged), the capability collects the distinct non-missing raw
values over the **whole** source. If there are at most `value_list_threshold`, `values` is
the list sorted by code point. Otherwise `values` is `null`. `distinct_count` is always
set. `fields[].name`, `fields[].type` and `sample` are computed exactly as today (FR-017).

**Rationale**:
- Keeping the list next to its field means the agent reads name, type, count and values
  together. A `null` list next to `distinct_count: 116` and the top-level
  `value_list_threshold: 30` is the "not listed because it has too many values" signal
  FR-015 asks for, without a separate status enum.
- Code-point order matches the text ordering `aggregate_rows` already uses (007
  research.md §7). It is stable and needs no locale. For the fields in scope (years, names)
  it is also the natural order.
- Distinct values are raw strings, so "Programa X" and "PROGRAMA X" stay two entries (spec
  edge case) and every listed value can be used as an exact `equals` value.
- Numeric-like fields are included when under the threshold (years, codes; spec
  Assumptions). Monetary fields have hundreds of distinct values and drop out naturally.

**Measured size (before)**: `inspect_schema("dados_gerais/tb_geral.csv").model_dump_json()`
is 5,994 characters today. The planned output adds `nome_unidade` (2), `nome_programa`
(13) and `data_ano` (20) lists. The after size is measured and recorded in results.md
(FR-019, Clarifications Q4).

**Alternatives considered**:
- *A separate `value_lists` map on the result*: splits one field's facts across two places.
  Rejected.
- *A dedicated `list_values(field)` tool*: an extra step per field out of a 10-step budget,
  and it relies on the model knowing to call it. The spec asks for the lists in inspection.
  Rejected.
- *Threshold on the sample instead of the source*: the exact failure the spec describes
  (`nome_unidade` has 2 values, the sample shows 1). Rejected.

## R6. Configuration: one typed `TextMatchingConfig`, injected and recorded

**Decision**: A frozen pydantic model in `data_access/text_matching.py`:

```text
TextMatchingConfig
  value_list_threshold: int = 30   (ge=0)
  max_suggestions: int = 5         (ge=1)
  stopwords: str = "pt_v1"         (must name an existing list)
```

- `data_access.capabilities.inspect_schema/query_rows/aggregate_rows` take a keyword
  argument `text_matching: TextMatchingConfig = TextMatchingConfig()`, so every existing
  call and test keeps working.
- `AgentSettings.text_matching: TextMatchingConfig` (default factory),
  `AgentDeps.text_matching` (default factory), and the three tool wrappers pass
  `ctx.deps.text_matching` through (Eng. 4). `_answer_with_selection` copies it from
  settings into deps.
- `QaAgentQuestionAnswerer` takes `text_matching` and exposes it as a property, as it does
  `history_char_limit`. The testset CLI passes the same object to the answerer and to the
  run, so the recorded value is the value used.
- `TestRun.text_matching` and `ConversationRun.text_matching`:
  `TextMatchingConfig | None = None`, where `None` means a pre-009 run. The CLI report
  prints one `Text matching: …` line.

No new CLI flag or environment variable: the defaults are the only values this feature
evaluates, and a knob with no current use is speculative (Principle VII). The settings
field keeps them overridable in code, and the run file records them either way (FR-016).

**Rationale**: Eng. 7 wants one typed, recorded settings object. The data access layer
cannot import `qa_agent`, so the model lives in `data_access` and `qa_agent` nests it.
Recording it on both run types lets a reader tell a 009 run apart from an earlier run by the
file alone. For the comparisons in this feature, that presence is also the version marker
for the changed tool descriptions (R7).

**Alternatives considered**:
- *Module constants like `SAMPLE_SIZE_CAP`*: FR-016 requires the values in the run record.
  A constant is not a recorded configuration. Rejected.
- *Flat fields on `AgentSettings`*: `data_access` would still need its own type to receive
  them. Rejected as duplication.

## R7. Tool descriptions: edit docstrings and field descriptions; prompts untouched

**Decision**: FR-018 is met in the tool schema the model sees:

- `query_rows` gains a docstring (today it has none) stating that `equals` compares the
  whole value ignoring case, accents and punctuation; that `contains` needs every word
  (except filler words like "de", "do") to start a word of the stored value, in any order;
  and that a 0-row result may carry `value_suggestions` with real stored values to retry
  with.
- `aggregate_rows`' docstring gets the same filter sentence and the suggestion sentence.
- `inspect_schema` gains a docstring stating that each field reports `distinct_count`, and
  that `values` lists every stored value when there are at most `value_list_threshold` of
  them (use those exact values in filters).
- `EqualsCondition.value` and `ContainsCondition.value` get a `Field(description=…)`
  with the short form of the rule, because the parameter schema is what the model reads
  when it builds the filter.

`system_v1.md` (standalone path) and `system_v2.md` (conversation path) are not edited, and
no new prompt version is added (Clarifications Q2).

**Note on the spec's prompt wording**: FR-018/FR-019 name `system_v2.md` because the
evidence run is a conversation run. The standalone `answer_question` path always renders
`system_v1.md` (008 FR-014), and so did the 008 standalone run `20260925T100203429266Z`.
"Same system prompt" therefore means each path keeps its own unchanged prompt: v2 for the
conversation test set, v1 for the standalone test set. Only the tool behavior and tool
descriptions differ between before and after.

**Rationale**: Tool descriptions are the one channel the spec allows. Docstrings are the
existing mechanism (007 used it for `aggregate_rows`), and `test_tools_description.py`
already captures tool definitions through a `FunctionModel`, so the new wording can be
asserted the same way.

## R8. Evaluation: two runs, two baselines, one reproducible analysis script

**Decision**:

| Test set | Before (008) | After (this feature) | Comparison |
|---|---|---|---|
| Conversations: `data/testsets/conversations/orcamentos-aeb-csv-conversations.json` | `20260925T095751382002Z` | one `run-conversations` run, same target/retry/history limit | `analyze_runs.py` (below) |
| Standalone: `data/testsets/orcamentos-aeb-csv-10.json` | `20260925T100203429266Z` | one `run` | `testset_runner compare` (0 `newly_failing` = SC-005) |

Target for both: `Qwen/Qwen3-8B-AWQ` at `http://localhost:8000/v1`, `--max-attempts 3`,
`--history-char-limit 16000` (the 008 conditions).

The standalone baseline is the 10-question set, not the 50-question
`orcamentos-aeb-csv.json`. Its most recent run (`20260925T111342801197Z`) was made before
commit `d196c05` edited that file. Its recorded `content_hash` (`81e631b8…`) no longer
matches the file (`01750b7a…`), so `compare` would reject it as incomparable. The
10-question file's hash (`178ba052…`) matches the 008 standalone run.

`specs/009-text-value-matching/analyze_runs.py` (same pattern as 008's
`build_conversation_testset.py`) prints, from recorded files only:

1. Per-category scored-turn rates for the before and after conversation runs, and the
   per-turn status transitions joined by `(conversation_id, turn_index)`.
2. For the after run, every `query_rows`/`aggregate_rows` step with an empty result. For
   each one: the text conditions, whether the value exists in the source (computed with
   the new matcher on the source), whether suggestions were returned, and whether the
   agent's next step used a suggested value. This makes the second clause of SC-004
   mechanically checkable.
3. The `inspect_schema` result size for `dados_gerais/tb_geral.csv`, before (the same
   result dumped without the 009 fields) and after.

**Rationale**: Principle I. Each number in results.md traces to a run id and a script over
recorded files. A per-turn conversation comparator in `testset_runner` is not required by
the spec, so it stays a feature-local script (Principle VII). If a later feature needs it
again, it can be promoted.

**Alternatives considered**:
- *Re-run the 50-question set twice (before on the old commit, after on the new one)*: it
  doubles model time and changes the baseline the spec names ("the single 008 run").
  Rejected.
- *Several runs per side*: rejected by Clarifications Q3. results.md states the noise
  caveat instead.
