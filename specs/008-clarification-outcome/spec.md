# Feature Specification: Clarification Outcome, Prompt v2 and Outcome-Based Grading

**Feature Branch**: `008-clarification-outcome`

**Created**: 2026-09-24

**Status**: Draft

**Input**: User description: "In test run 20260924T121028315459Z, the agent guessed on two edge-case questions: #49 'valor do orçamento da AEB em 2005' (it chose dotação on its own; the four measures differ by up to 36%; the testset expects a clarifying question) and #48 'merenda escolar' (no such item; the agent said so, then gave 'Assistência Pré-escolar' as a substitute). Also, #48 and #50 were reported as 'partial' instead of 'none', #50 wrote 'Classificação: partial.' into its answer, and these cases always land in needs_review, so regressions go unnoticed. Requirements: (1) a fourth outcome 'needs_clarification'; (2) prompt v2 (system_v2.md, v1 unchanged, version selectable and recorded per test run) plus briefing guidance on which wording picks which measure; (3) an optional expected_outcome on testset records that drives grading; set #48 and #50 to 'none' and #49 to 'needs_clarification'. Acceptance: with v2 the three questions grade as matched, no other question asks for clarification and nothing that passed under v1 regresses; with v1 the same three questions grade as not_matched."

## Clarifications

### Session 2026-09-24

- Q: Which prompt version is the default when none is selected? → A: v2. v1 stays available and must be selected explicitly (e.g. for the SC-002 baseline run).
- Q: When grading a "none" or "needs_clarification" answer, how should digits that are part of a name (e.g. "Amazônia-1") be treated? → A: Only numbers that look like amounts or percentages fail the check ("R$", a decimal or thousands separator, or "%"). Plain integers, including years, list markers and digits in names, are allowed.
- Q: The briefing is edited in place, but Engineering Principle 8 says briefing content is never edited in place and must be referenced by the run that used it. How should this be handled? → A: Edit the briefing in place, and have each test run also store a content fingerprint (hash) of the briefing it used.
- Q: How is model randomness handled when judging SC-001–SC-005? → A: Single run, strict. Any failure in that run fails acceptance. No re-runs to confirm or overturn a result.

## Evidence

- **Run**: `20260924T121028315459Z`, testset `data/testsets/orcamentos-aeb-csv.json`, prompt `system_v1.md`.
- **#49** ("Qual foi o valor do orçamento da Agência Espacial Brasileira em 2005?"): the agent picked `dotação atual` on its own. Dotação, empenhado, liquidado and pago differ by up to 36% for this question. The testset expects a clarifying question. Prompt v1 rule 4 tells the agent to pick the most reasonable reading, so v1 causes this.
- **#48** ("Quanto a Agência Espacial Brasileira gastou com merenda escolar em 2005?"): the dataset has no such action. The agent said so, then reported the value of "Assistência Pré-escolar" as a substitute and labelled the outcome "partial".
- **#50** ("Quanto foi pago pelo desenvolvimento do satélite Amazônia-1 em 2020?"): the year is not covered. The agent reported the outcome "partial" instead of "none" and wrote "Classificação: partial." in the answer text. Prompt v1 rule 8 asks the agent to "classify" its result without saying where, so v1 invites this.
- **Grading gap**: the expected values for #48–#50 are not numbers, so the grader always marks them `needs_review`. None of the failures above showed up in the match rate.

## User Scenarios & Testing *(mandatory)*

The actors are (a) **the person asking questions** (web UI or harness) and (b) **the researcher** who runs the testset to measure the agent and compare prompt versions.

### User Story 1 - Agent asks instead of guessing on ambiguous questions (Priority: P1)

A person asks a question that could mean more than one measure, and the readings give different amounts (e.g. "o orçamento da AEB em 2005" could mean dotação, empenhado, liquidado or pago). The agent does not pick one. It replies in Portuguese with a clarifying question that lists the possible readings in plain language, gives no amounts, and reports the outcome "needs clarification".

**Why this priority**: Picking one reading silently can give an answer that is off by a third, presented as fact. That is the most harmful behavior observed, and it goes against the project's rule of never stating what the data doesn't support.

**Independent Test**: Ask #49 with prompt v2. Check that the outcome is "needs clarification" and that the answer is a Portuguese question naming the readings, with no amounts.

**Acceptance Scenarios**:

1. **Given** prompt v2 and the question "Qual foi o valor do orçamento da Agência Espacial Brasileira em 2005?", **When** the agent answers, **Then** the outcome is "needs clarification" and the answer asks the person to choose between the readings (authorized budget, committed, liquidated, paid), described in plain Portuguese and not as field names.
2. **Given** a clarifying answer, **When** it is inspected, **Then** it contains no monetary amount or other value from the dataset.
3. **Given** the agent asks for clarification without running any data query, **When** the result is finalized, **Then** the outcome stays "needs clarification" and is not downgraded to "none".
4. **Given** a question whose wording already names the measure (e.g. "quanto foi pago", "quanto foi gasto", "qual foi o orçamento previsto"), **When** the agent answers with prompt v2, **Then** it answers with that measure and does not ask for clarification.
5. **Given** an ambiguous question where all readings give the same amount, **When** the agent answers, **Then** it answers directly (no clarification needed) and says the readings agree.

---

### User Story 2 - Agent reports "none" cleanly when nothing matches (Priority: P1)

A person asks about an item or period the dataset doesn't contain. The agent says plainly that the data isn't available. It doesn't offer a similar item's value as a substitute, reports the outcome "none", and keeps outcome labels out of the answer text.

**Why this priority**: Giving a neighbouring item's value as a stand-in (#48) is a made-up answer in effect. A wrong outcome label (#48, #50) corrupts the usage record the project relies on (Principle X).

**Independent Test**: Ask #48 and #50 with prompt v2. Check that each outcome is "none", that the answer states unavailability, and that it contains no amounts or outcome labels.

**Acceptance Scenarios**:

1. **Given** prompt v2 and question #48 (merenda escolar), **When** the agent answers, **Then** the outcome is "none", the answer says the dataset has no such item, and it doesn't mention or give a value for any other item as a substitute.
2. **Given** prompt v2 and question #50 (Amazônia-1 in 2020), **When** the agent answers, **Then** the outcome is "none" and the answer says the period/record isn't covered.
3. **Given** any answer produced with prompt v2, **When** its text is inspected, **Then** it contains no outcome label ("full", "partial", "none", "needs_clarification" or a "Classificação:" line). The outcome appears only in the outcome field.

---

### User Story 3 - Outcome-based automatic grading (Priority: P1)

The researcher marks testset records with the outcome they expect. The grader then marks those records matched or not_matched on its own, without a person reviewing them, so a regression on these questions shows up in the match rate and in run comparisons.

**Why this priority**: Without it, User Stories 1 and 2 can't be measured, and a later change could break them without anyone noticing (Principle I).

**Independent Test**: Grade hand-built results for a record with an expected outcome (right outcome, wrong outcome, right outcome with a leaked amount). Check the statuses. Then grade a record without an expected outcome and check that the status is the same as today.

**Acceptance Scenarios**:

1. **Given** a record with expected outcome "none" and an agent result with outcome "none" whose answer contains no amount or percentage (plain integers such as years or "Amazônia-1" are fine), **When** it is graded, **Then** it is matched.
2. **Given** the same record and an agent result with outcome "partial", **When** it is graded, **Then** it is not_matched.
3. **Given** a record with expected outcome "needs_clarification" and an agent result with that outcome whose answer contains a monetary amount, **When** it is graded, **Then** it is not_matched.
4. **Given** a record with expected outcome "full" and a numeric expected value, **When** it is graded, **Then** it is matched only if the outcome is "full" and the expected number is found in the answer as today. A wrong outcome gives not_matched.
5. **Given** a record without an expected outcome, **When** it is graded, **Then** the status is the same as the current grader gives.
6. **Given** an errored question, **When** it is graded, **Then** it stays errored whatever its expected outcome.
7. **Given** the bundled testset, **When** it is loaded, **Then** #48 and #50 carry expected outcome "none" and #49 carries "needs_clarification", and no other record changes.

---

### User Story 4 - Selectable, recorded prompt version (Priority: P2)

The researcher picks which prompt version (v1 or v2) the agent uses for a testset run or a session. Each test run records the version it used, so v1 and v2 runs can be compared side by side and reproduced later.

**Why this priority**: The acceptance criteria compare v1 against v2 on the same testset, and Engineering Principle 8 requires prompts to be named, versioned and referenced by the run that used them.

**Independent Test**: Run a small testset once with v1 and once with v2. Check that each stored run records its prompt version, that the v1 prompt text is byte-for-byte unchanged, and that comparing the two runs shows both versions.

**Acceptance Scenarios**:

1. **Given** no prompt version is chosen, **When** the agent runs (testset runner, harness or web UI), **Then** it uses the default version (v2) and a test run records "v2".
2. **Given** prompt version v1 is chosen, **When** a testset run completes, **Then** the stored run records "v1".
3. **Given** a prompt version that doesn't exist (e.g. "v9"), **When** a run is started, **Then** it is refused before any question is asked, with an error that names the invalid version and lists the available ones.
4. **Given** a run stored before this feature, **When** it is loaded, **Then** it loads without error and its prompt version and briefing fingerprint are reported as not recorded.
5. **Given** two runs of the same testset with different prompt versions, **When** they are compared, **Then** the comparison shows each run's prompt version and briefing fingerprint. These are shown for information only and don't change how transitions are computed.
6. **Given** two runs made with the same briefing text, **When** their stored records are inspected, **Then** both record the same briefing fingerprint. After the briefing text changes, a new run records a different fingerprint.

---

### Edge Cases

- **Clarification after some queries**: the agent may query data before deciding the question is ambiguous (e.g. to check whether the readings differ). The outcome is still "needs clarification", and the answer must still contain no dataset values.
- **Readings that agree**: if every reading gives the same amount, no clarification is needed. The agent answers directly (User Story 1, scenario 5).
- **Question that is both ambiguous and not covered** (e.g. "orçamento da AEB em 2025"): the lack of coverage wins. The outcome is "none", because asking which measure the person means would be pointless.
- **"Full" or "partial" reported with zero successful queries**: still downgraded to "none" as today. Only "needs clarification" is exempt from the downgrade.
- **Numbers in clarifying or "none" answers**: only numbers that look like amounts or percentages make the record not_matched: a number preceded by "R$", a number with a decimal or thousands separator (e.g. "1.234", "12,5"), or a number followed by "%". Plain integers are allowed, including years ("2005"), list markers ("1." at the start of a line, "2)") and digits in names ("Amazônia-1"). A small count written as a plain integer is therefore not caught.
- **Expected outcome with a non-numeric expected value for "full"/"partial"**: the outcome must match. If it does, the numeric check gives needs_review as today. If it doesn't, the record is not_matched.
- **Invalid expected outcome value in a testset file**: the testset is refused at load time with the existing invalid-testset error, naming the record.
- **Comparing runs across the testset edit**: adding expected outcomes changes the testset content, so runs made before the edit can't be compared with runs made after it, as today. The v1-vs-v2 comparison uses two new runs.
- **Web UI**: a clarifying answer is shown like any other answer. The person answers by asking a new, more specific question. There is no multi-turn follow-up (see Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

**Outcome**

- **FR-001**: The set of agent outcomes MUST include a fourth value, "needs_clarification", alongside "full", "partial" and "none".
- **FR-002**: Every place an outcome is produced, stored or reported MUST accept "needs_clarification": the agent's structured answer, the question-answering result, the usage/run log entry, and each test-run question result.
- **FR-003**: Run files and log files written before this feature MUST still load without error or migration.
- **FR-004**: An outcome of "needs_clarification" MUST NOT be downgraded to "none" because no data query succeeded. The existing downgrade still applies to "full" and "partial".

**Prompt v2 and briefing**

- **FR-005**: A second system prompt version (v2) MUST be added as a new, separate artifact. The v1 prompt MUST remain byte-for-byte unchanged.
- **FR-006**: Prompt v2 MUST instruct the agent to:
  - ask a clarifying question, not choose, when a question could mean more than one measure and the readings give different amounts;
  - write the clarifying question in Portuguese, list the possible readings in plain language, and include no values from the dataset;
  - never offer a similar or related item's value as a substitute when nothing in the dataset matches, and report "none" in that case;
  - report the outcome only in the outcome field, never in the answer text.
  All other v1 rules (Portuguese, grounding, no internal identifiers, plain-language failures) MUST be carried over.
- **FR-007**: The dataset briefing for `orcamentos-aeb-csv` MUST state which wording selects which measure when the question already specifies it. At minimum: "gasto"/"pago"/"pagamento" selects paid, "orçamento previsto"/"dotação"/"autorizado" selects authorized budget, "empenhado" selects committed and "liquidado" selects liquidated. Unqualified "orçamento"/"valor do orçamento" is ambiguous. This guidance MUST live in the briefing, not in the prompt, because it is specific to one dataset (Principle V).
- **FR-008**: The prompt version MUST be selectable through the agent's typed configuration and through the testset runner. When nothing is selected, the default is v2, in every entry point (testset runner, harness and web UI). v1 MUST remain selectable.
- **FR-009**: Selecting a prompt version that doesn't exist MUST fail before any question is asked, with an error naming the requested version and listing the available ones.
- **FR-010**: Each test run MUST record the prompt version it used and a content fingerprint (hash) of the dataset briefing it used. Two runs made with the same briefing text MUST record the same fingerprint, and a change to the briefing text MUST change it. Runs stored before this feature MUST load with both the prompt version and the briefing fingerprint reported as not recorded.
- **FR-011**: A comparison of two runs MUST show each run's prompt version and briefing fingerprint for information, and MUST say whether the fingerprints differ. It MUST NOT affect how transitions are computed.

**Grading**

- **FR-012**: Testset records MUST accept an optional expected outcome, restricted to the four outcome values. An invalid value MUST make the testset fail to load with the existing invalid-testset error.
- **FR-013**: When a record has an expected outcome, the agent's outcome MUST equal it. Otherwise the record is not_matched.
- **FR-014**: When the expected outcome is "none" or "needs_clarification" and the outcomes match, the record is matched only if the answer contains no number that looks like an amount or percentage: a number preceded by "R$", a number containing a decimal or thousands separator, or a number followed by "%". Plain integers (years, list markers, digits in names such as "Amazônia-1") are allowed. Otherwise it is not_matched. The record's expected text is not used in this case.
- **FR-015**: When the expected outcome is "full" or "partial" and the outcomes match, the record's status MUST come from the existing expected-value check (matched / not_matched / needs_review).
- **FR-016**: Records without an expected outcome MUST be graded exactly as they are today.
- **FR-017**: Errored questions MUST remain errored whatever their expected outcome.
- **FR-018**: Each test-run question result MUST record the expected outcome it was graded against, or none if the record had none.
- **FR-019**: The bundled testset MUST set expected outcome "none" on #48 and #50 and "needs_clarification" on #49. No other record changes.
- **FR-020**: The grading rules MUST be deterministic and usable without the agent framework or a model, so they can be tested directly (Principle VI, Engineering Principle 6).

### Key Entities

- **Outcome**: the agent's own classification of its result. One of full, partial, none, needs_clarification.
- **Prompt version**: a named, immutable system prompt (v1, v2). It is selected per run and recorded on each test run.
- **Dataset briefing**: dataset-specific guidance put into the prompt. It gains a wording-to-measure section. It is identified on each test run by a content fingerprint.
- **Testset record**: an existing question record plus an optional expected outcome.
- **Question result**: an existing per-question result that also records the expected outcome it was graded against. Its agent outcome can now be needs_clarification.
- **Test run**: an existing run record that also records the prompt version and the briefing fingerprint. Neither is recorded for older runs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a full testset run with prompt v2, #49 returns a clarifying question, and #48, #49 and #50 all grade as matched (3 of 3).
- **SC-002**: In a full testset run with prompt v1 (selected explicitly) on the updated testset, #48, #49 and #50 all grade as not_matched (3 of 3). This confirms the new grading catches the old behavior.
- **SC-003**: In the v2 run, no question other than #49 has the outcome "needs clarification" (0 of 49).
- **SC-004**: Comparing the v1 and v2 runs (same testset, same model) shows 0 questions that are matched under v1 and not matched under v2.
- **SC-005**: In the v2 run, 0 answers contain an outcome label in the answer text.
- **SC-006**: Every run file and log file stored before this feature loads without error (100%), including the recorded run `20260924T121028315459Z`.
- **SC-007**: Regrading stored results for records without an expected outcome gives the same status for 100% of them.
- **SC-008**: #48, #49 and #50 leave the needs_review bucket. The needs_review count of a v2 run is at least 3 lower than that of run `20260924T121028315459Z`.

## Assumptions

- **Truncated input filled in**: parts of the feature description were cut off. They are read as follows: prompt v2 also tells the agent to report the outcome only in the outcome field and never in the answer text. "Gasto"/"pago" means paid, "orçamento previsto" means authorized budget (dotação), and unqualified "orçamento" is ambiguous. For "none"/"needs_clarification" the answer must contain no dataset values, checked as "no amounts or percentages" (see Clarifications and FR-014). Records without an expected outcome are graded exactly as today. With v2, #49 returns a clarifying question and #48–#50 grade as matched. No other question asks for clarification, and nothing that matched under v1 regresses under v2.
- **v2 is the default prompt** (see Clarifications): the agent's behavior changes for everyone who doesn't select a version, including web UI sessions. Runs stored before this feature don't record a version. They were made with v1, but they are reported as "not recorded" rather than inferred.
- **The briefing is edited in place and shared by both prompt versions** (see Clarifications): v1 runs after this change see the new wording guidance too. This departs from Engineering Principle 8's "never edited in place". It is made acceptable by storing the briefing fingerprint on every test run, so the briefing a run used is always identifiable. The briefing adds guidance and doesn't override v1's "pick the most reasonable reading" rule, so the v1 baseline in SC-002 still shows the old guessing behavior. Named briefing versions and briefing selection are out of scope. Only the fingerprint is recorded.
- **Clarification is single-turn**: the agent returns a clarifying question and the exchange ends. The person asks again with a more specific question. Multi-turn conversation state is out of scope.
- **"Values from the dataset" is checked by the number rule**: grading approximates "no dataset values" as "no amounts or percentages" (see FR-014). Every monetary value in this dataset is an amount, so a leaked value is caught. Plain integers are not checked, and neither are item names. Substituted item names (as in #48) are prevented by the prompt and caught by the outcome check whenever the agent labels such an answer "partial".
- **Recording the prompt version in the usage log** is out of scope. This feature records it on test runs only, as requested.
- **LLM variability** (see Clarifications): SC-001 through SC-005 are judged strictly on one v1 run and one v2 run with the configured model. Any failure in those runs fails acceptance. It is not re-run to confirm or overturn the result, and the grading is not changed to make it pass. A failure is fixed by changing the prompt or briefing and doing a new pair of runs.
