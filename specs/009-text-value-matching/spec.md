# Feature Specification: Forgiving Text Matching and Value Suggestions

**Feature Branch**: `009-text-value-matching`

**Created**: 2026-09-25

**Status**: Draft

**Input**: User description: "Currently, some questions are failing due to the agent being unable to find the real text values on the datasets, which is evidenced by specs/008-chat-conversation-history/results.md. To fix this, we should normalize text before matching. equals and contains should ignore case, accents, hyphens and punctuation, and contains should skip stopwords. Also, we should suggest the closest real values when a filter returns 0 rows. Rank them by token overlap, and include acronyms. Finally, we should list all values of low-cardinality fields in inspect_schema, allowing the agent to pick values easily on columns with little value variations."

## Evidence _(Constitution Principle II)_

Run `20260925T095751382002Z` in `specs/008-chat-conversation-history/results.md`, "Why the failing turns failed", cause 1: the agent filtered `nome_unidade equals "AEB"` or `nome_acao equals "desenvolvimento do satélite Amazônia-1"`, got 0 rows and declined. The real values are "Agência Espacial Brasileira" and an action name spelled differently. This cause alone accounts for the whole `follow-up-metric` category (0/3), `follow-up-reference-02`, and the context turn of `follow-up-metric-01`. In each case the data held the answer, but the agent could not reach the stored text. Nothing in the 0-row result told the agent what the stored values look like.

In the evaluated source (`dados_gerais/tb_geral.csv`), `nome_unidade` has only 2 distinct values and `nome_programa` has 13. The agent sees these only if they happen to appear in the 20-row sample `inspect_schema` returns today.

## Clarifications

### Session 2026-09-25

- Q: When `contains` checks each filter word against a stored value, should the word match only at the start of a stored word, or anywhere inside the value? → A: At the start of a stored word ("satel" matches "Satélite", "4" does not match "2014"). Suggestion ranking uses the same rule.
- Q: Should this feature change only the tool descriptions and keep the system prompt at `system_v2.md` for the before/after evaluation? → A: Yes. Only the tool descriptions change, and the system prompt stays `system_v2.md` so the comparison with the 008 runs isolates this feature.
- Q: How many times should each test set be run for the "after" measurement? → A: Once per test set, compared with the single 008 run. The results document notes that a single run is noisy on small categories.
- Q: Besides the 30-distinct-values threshold, should schema inspection limit how much text it lists, for example by skipping fields whose values are long? → A: No. There is only the per-field threshold and no size cap. The inspection output size is recorded in the results as evidence for a possible later cap.

## User Scenarios & Testing _(mandatory)_

The "user" of these capabilities is the question-answering agent. It calls `inspect_schema`, `query_rows` and `aggregate_rows` while answering a natural-language question about a Brazilian open dataset. The people who ask the questions benefit indirectly: fewer wrong "no data found" answers.

### User Story 1 - Text filters tolerate differences in writing (Priority: P1)

The agent filters a text field with a value that names the right thing but is written differently from the stored text: different case, missing or extra accents, a hyphen instead of a space, extra punctuation, or (for `contains`) filler words such as "do" and "de" that the stored text lacks or places elsewhere. The filter still matches the intended rows.

**Why this priority**: This is the direct cause of the failures in the evidence. It needs no change in model behavior. The same filter the agent already writes starts to match, so it works without prompt changes.

**Independent Test**: Run `query_rows` and `aggregate_rows` on a fixture source with values such as "Agência Espacial Brasileira" and "Projeto CBERS-4". Use filter values that differ only in case, accents, hyphens, punctuation and stopwords. Check that the matched rows equal the hand-computed set.

**Acceptance Scenarios**:

1. **Given** a stored value "Agência Espacial Brasileira", **When** the agent filters `equals "agencia espacial brasileira"`, **Then** the rows with that value match.
2. **Given** a stored value "Projeto CBERS-4", **When** the agent filters `equals "projeto cbers 4"`, **Then** the rows match (a hyphen counts the same as a space).
3. **Given** a stored value "Ministério da Ciência, Tecnologia, Inovações e Comunicações", **When** the agent filters `equals "Ministerio da Ciencia Tecnologia Inovacoes e Comunicacoes"`, **Then** the rows match (punctuation is ignored and repeated spaces count as one).
4. **Given** a stored value "Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS-3", **When** the agent filters `contains "desenvolvimento de satelite sino brasileiro"`, **Then** the rows match: stopwords ("de", "do") in the filter value are skipped, and the remaining words are compared with accents, case and hyphens ignored.
5. **Given** a stored value "Agência Espacial Brasileira", **When** the agent filters `equals "Agência Espacial"`, **Then** it does not match. `equals` still requires the whole normalized value to match, only compared after normalization.
6. **Given** a numeric range filter, **When** the agent queries, **Then** its behavior is unchanged.
7. **Given** a filter whose value was already an exact match before this change, **When** the agent queries, **Then** it matches exactly the same rows as before.

---

### User Story 2 - A zero-row result suggests the closest real values (Priority: P2)

When a text filter matches no rows, the result tells the agent which stored values of that field come closest to what it asked for. The agent can then retry with a real value instead of declining.

**Why this priority**: Normalization cannot bridge abbreviations and paraphrases ("AEB" vs "Agência Espacial Brasileira"). Suggestions close that gap in a way the agent can check and act on. It builds on US1 because suggestions are computed from normalized text.

**Independent Test**: Run `query_rows` and `aggregate_rows` with filters known to match nothing on a fixture source. Check that each result carries the expected suggestions, in the expected order, for the expected field.

**Acceptance Scenarios**:

1. **Given** a field whose stored values include "Agência Espacial Brasileira", **When** the agent filters `equals "AEB"` and gets 0 rows, **Then** the result suggests "Agência Espacial Brasileira", because "AEB" matches the acronym of that value.
2. **Given** a field whose values include "Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS-4" and "Projeto CBERS-3", **When** the agent filters `contains "satélite CBERS 5"` and gets 0 rows, **Then** the suggestions are ordered by how many filter words each value shares, with the value that shares the most first.
3. **Given** a query with several conditions where one text condition on its own matches no rows, **When** the combined query returns 0 rows, **Then** suggestions are given for that condition's field. Conditions that match rows on their own get no suggestions.
4. **Given** a query where every condition matches rows on its own but their combination matches none, **When** the query returns 0 rows, **Then** no suggestions are given. The result stays a correct empty result, so the agent can tell "value not found" apart from "no rows for this combination".
5. **Given** a filter value that shares no word or acronym with any stored value, **When** it matches 0 rows, **Then** the result reports that no close values were found rather than suggesting unrelated values.
6. **Given** any query that returns at least one row, **When** the result is produced, **Then** it contains no suggestions.
7. **Given** a numeric range filter that matches no rows, **When** the result is produced, **Then** no text suggestions are given for it.

---

### User Story 3 - Schema inspection lists every value of low-cardinality fields (Priority: P3)

When the agent inspects a source, every field with few distinct values is reported together with the complete list of those values. The agent can then pick a real value before it ever writes a filter.

**Why this priority**: It prevents the failure in the first place, not just recovers from it. It depends on the agent reading the list, so its effect on answers is less direct than US1 and US2.

**Independent Test**: Inspect a fixture source that has one field with 3 distinct values, one with exactly the threshold number, and one with more. Check which fields carry a full value list and that each list is complete.

**Acceptance Scenarios**:

1. **Given** a field with 2 distinct values across the whole source (e.g. `nome_unidade`), **When** the agent inspects the source, **Then** both values are listed for that field, even if only one appears in the returned sample rows.
2. **Given** a field whose number of distinct values is at or below the threshold, **When** the agent inspects the source, **Then** all its distinct non-missing values are listed exactly as stored, in a stable order.
3. **Given** a field with more distinct values than the threshold (e.g. `nome_acao` with 116), **When** the agent inspects the source, **Then** no value list is given for it, and the result shows that the field was not listed because it has too many values.
4. **Given** a field that is missing in some rows, **When** its values are listed, **Then** the missing value is not listed as a value.
5. **Given** the existing fields, types and sample rows, **When** the agent inspects a source, **Then** they are reported exactly as before. The value lists are added, nothing is removed.

---

### Edge Cases

- A filter value that is empty, or becomes empty after normalization (e.g. "-" or "..."): `contains` matches every row with a value (as an empty substring does today); `equals` matches only values that also normalize to empty.
- A `contains` filter made only of stopwords (e.g. "de"): the stopwords are kept rather than skipped, so the filter is not reduced to nothing.
- Stored values that differ only in case, accents or punctuation (e.g. "Programa X" and "PROGRAMA X"): `equals` on either matches both. Suggestions and value lists still show each stored spelling separately.
- Missing values never match `equals` or `contains` and are never suggested.
- A short `contains` word that occurs inside a longer stored word (e.g. `contains "cbers 4"` against "Projeto CBERS-14" or a value holding "2014"): it does not match, because filter words match only at the start of a stored word. It still matches "CBERS-4A".
- A numeric-looking field filtered with `equals` (e.g. `data_ano equals "2012"`): normalization applies the same way and changes nothing for plain digits.
- Characters outside Latin script, or symbols such as "º", "ª", "§", "%": they are handled consistently on both sides of the comparison, so a value always matches itself.
- A field with a huge number of distinct values: suggestion ranking must still finish within the normal response time of a query.
- Two suggestions with the same score: the order is deterministic (the same inputs always give the same order).

## Requirements _(mandatory)_

### Functional Requirements

**Normalization (US1)**

- **FR-001**: Text comparison for `equals` and `contains` MUST normalize both the filter value and the stored value before comparing: case-folded, accents removed, hyphens and other punctuation treated as word separators, and runs of whitespace collapsed to single spaces, with leading and trailing whitespace removed.
- **FR-002**: `equals` MUST match a row when the normalized stored value equals the normalized filter value in full.
- **FR-003**: `contains` MUST match a row when every non-stopword word of the normalized filter value is a prefix of some word of the normalized stored value (e.g. "satel" matches "satelite"; "4" does not match "2014"). If the filter value has only stopwords, its words MUST be used as they are.
- **FR-004**: The stopword list MUST be a named, versioned configuration artifact, not a list embedded in the matching logic (Principle V). The default list covers common Portuguese articles, prepositions and their contractions, and conjunctions.
- **FR-005**: Normalization MUST apply the same way wherever `equals` and `contains` are accepted: row queries and aggregation filters.
- **FR-006**: Normalization MUST NOT change stored values in any result. Rows, groups, sample rows, suggestions and value lists show values exactly as stored.
- **FR-007**: Range filters, numeric classification and every other existing behavior MUST stay unchanged.

**Suggestions (US2)**

- **FR-008**: When a row query or aggregation returns 0 rows or 0 groups, the result MUST include suggestions for each `equals`/`contains` condition that matches no rows of the source on its own.
- **FR-009**: Suggestions for a condition MUST be distinct stored values of that condition's field. Candidates are ranked by token overlap: the number of non-stopword words of the normalized filter value that are a prefix of some word of the normalized stored value or of its acronym (the same word-start rule as `contains`).
- **FR-010**: A stored value's acronym MUST be taken into account when ranking. The acronym is formed from the first letters of its non-stopword words (e.g. "Agência Espacial Brasileira" → "AEB"). All-caps words already in the value (e.g. "CBERS") count as words as they are.
- **FR-011**: Only values with an overlap of at least one MUST be suggested, up to a fixed maximum per condition (default 5). Ties MUST be broken deterministically (e.g. by more rows having the value, then alphabetically).
- **FR-012**: Each suggestion MUST name the field and the condition it answers, so the agent can retry with a corrected filter.
- **FR-013**: A result with at least one row or group MUST NOT include suggestions. Its shape MUST otherwise be unchanged.

**Low-cardinality value lists (US3)**

- **FR-014**: Schema inspection MUST list every distinct non-missing stored value for each field whose count of distinct values across the whole source is at or below a threshold (default 30). Values are listed exactly as stored, in a stable order. The threshold is the only limit: there is no cap on value length or on the total size of the lists (Principle VII).
- **FR-015**: For fields above the threshold, schema inspection MUST report that the values were not listed, and the number of distinct values.
- **FR-016**: The threshold and the suggestion maximum MUST be part of the typed, recorded run configuration (Engineering Principle 7), so every evaluation run records the values it used.
- **FR-017**: The existing schema inspection output (fields, types, sample rows) MUST be unchanged.

**Guidance and evidence**

- **FR-018**: The tool descriptions the agent sees MUST state that text filters ignore case, accents and punctuation, that a zero-row result may carry suggestions to retry with, and that inspection lists all values of low-cardinality fields. The system prompt MUST stay `system_v2.md`, unchanged: this feature does not add a new system prompt version, so the before/after comparison measures only the tool changes (Engineering Principle 8, Principle II).
- **FR-019**: The feature MUST be evaluated with a recorded before/after comparison on both the standalone test set and the conversation test set against the same model, settings and system prompt (`system_v2.md`) as the 008 evidence run (Principles I and II). The only difference between the runs is this feature's tool behavior and tool descriptions. Each test set is run once after the change and compared with the single 008 run on it. The results MUST be written to this feature's results document, including the size of the `inspect_schema` result for the evaluated source before and after the change, and that document MUST state that one run per side is noisy for small categories (e.g. the 3 `follow-up-metric` conversations).

### Key Entities

- **Normalized text**: the comparison form of a filter value or stored value (case-folded, accent-free, punctuation as spaces, collapsed whitespace). Used only for comparing, never shown.
- **Stopword list**: a named, versioned set of words that `contains` and suggestion ranking skip.
- **Value suggestion**: for one zero-match text condition, the field name, the condition's value, and an ordered list of stored values with their overlap scores.
- **Field value list**: for one low-cardinality field in a schema inspection result, all its distinct stored values. For a field above the threshold, its distinct-value count and a "not listed" marker.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: On fixture sources, 100% of filter values that differ from a stored value only in case, accents, hyphens, punctuation or whitespace match that value's rows with `equals` and `contains`. The same holds with stopwords added or removed for `contains`.
- **SC-002**: The filter values that failed in the 008 evidence run ("AEB" for `nome_unidade`, and the Amazônia-1 / CBERS action names) each either match the intended rows or produce a suggestion list with the intended stored value in the top 3.
- **SC-003**: For every low-cardinality field of the evaluated dataset (e.g. `nome_unidade`, `nome_programa`, `data_ano`), schema inspection lists 100% of its distinct values.
- **SC-004**: In a re-run of the conversation test set under the 008 evidence conditions, at least 2 of the 3 `follow-up-metric` conversations are scored correct (from 0/3). No turn fails because a text filter returned 0 rows while the intended value existed in the source.
- **SC-005**: In a re-run of the standalone test set under the same conditions, no question that passed in the most recent baseline run fails (0 newly failing in `compare`).
- **SC-006**: Every existing test for exact-match filters, range filters, aggregation and schema inspection still passes unchanged.

## Assumptions

- `equals` stays a whole-value comparison after normalization. It does not match acronyms or partial values. Acronyms are used only for ranking suggestions, so a filter never silently matches a value the agent did not name.
- "Skip stopwords" applies to `contains` and to suggestion ranking, not to `equals`. `contains` also changes from one contiguous substring to "every remaining word appears, in any order". This is the behavior the description asks for. A partial word still matches when it is the start of a stored word (e.g. "satel" matches "Satélite"), but a filter word never matches inside a stored word (e.g. "4" does not match "2014" or "CBERS-14").
- Suggestions are computed only when the result is empty. The per-condition check (whether each condition matches rows on its own) reuses the same source already read for the query.
- The low-cardinality threshold defaults to 30. It lists `nome_unidade` (2), `nome_programa` (13) and `data_ano` (20) in the evaluated source and leaves out `nome_acao` (116) and the monetary fields. Numeric-like fields are included when they fall under the threshold, because years and codes are useful to pick from too.
- The stopword list is Portuguese by default because every current dataset is Brazilian. Other languages are supported by supplying another list, not by code changes.
- Model-level outcomes (SC-004) depend on the model using suggestions and value lists. The mechanism-level criteria (SC-001–SC-003, SC-006) are the ones this feature guarantees. SC-004 and SC-005 are measured and reported whether or not they are met, the same way 008 reported its results.
- The `aggregate_rows` mental-arithmetic failures, the missing declines for context-free follow-ups, and the rare clarification requests (008 causes 2–4) are out of scope. So is any system prompt change, such as a rule to retry with a suggested value before declining. If the measured results show one is needed, it becomes a separate, separately evaluated change.
