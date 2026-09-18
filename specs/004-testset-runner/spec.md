# Feature Specification: Testset Runner for LLM Evaluation

**Feature Branch**: `004-testset-runner`

**Created**: 2026-09-18

**Status**: Draft

**Input**: User description: "We need to develop an easy, reproducible and comparable way of running testsets against llm models. There is a sample testset on ./data/testsets/orcamentos-aeb-csv.json. It should be easy to select the url and the model used in a test run. The output of a test run should provide clear ways of improving the application, making it easy to identify what the agent did on each question. Each question should be asked in an isolated way."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run the sample testset and see what went wrong per question (Priority: P1)

A person improving the agent picks a testset (starting with the bundled `orcamentos-aeb-csv.json`, which has 50 Portuguese budget questions with their expected answers), picks which model and which endpoint/provider URL the agent should use, and starts a run. When it finishes, they get a report that goes question-by-question: what was asked, what the agent answered, what was expected, whether it matched, which dataset the agent picked, and the steps it took to get there — enough detail to tell, for any wrong answer, whether the agent picked the wrong dataset, misread a field, gave up too early, or something else.

**Why this priority**: This is the entire point of the feature. Without a trustworthy, detailed per-question breakdown from a single run, there is nothing to compare and nothing to act on. This alone is a usable MVP.

**Independent Test**: Point a run at the sample testset and any configured model/URL, let it finish, and confirm the report lists all 50 questions with expected vs. actual answers, a match indicator, and the dataset/steps the agent used for each one — without needing to dig through raw application logs to explain any single result.

**Acceptance Scenarios**:

1. **Given** the bundled sample testset and a chosen model + URL, **When** a person starts a run, **Then** the system asks every question in the testset and produces one report covering all of them.
2. **Given** a completed run's report, **When** a person looks at any single question, **Then** they can see the question, the expected answer, the agent's actual answer, whether it matched, which dataset the agent selected, and the retrieval steps the agent took — all in one place, without re-running anything.
3. **Given** a question whose expected answer is a plain value (e.g., a number), **When** the agent's answer is checked against it, **Then** the report clearly marks it as matching or not matching.
4. **Given** a question whose expected answer is not a plain value (e.g., "data not available" for an edge case), **When** the agent's answer is checked, **Then** the report flags it for the person's own judgment rather than silently guessing right or wrong.
5. **Given** one question in the run errors out (e.g., the model call fails), **When** the run continues, **Then** every other question is still asked and answered, and the failed question is recorded as errored rather than silently dropped or aborting the whole run.

---

### User Story 2 - Compare two runs to see what changed (Priority: P2)

A person has run the same testset before and after changing something (a different model, a different prompt, a code fix) and wants to know, without manually diffing two reports by eye, exactly which questions newly started passing, which newly started failing, and which are still failing either way.

**Why this priority**: Running once tells you where you stand; comparing runs is what turns this into a tool for *improving* the application over time, which is the stated goal. It depends on User Story 1 already producing structured, persisted results.

**Independent Test**: Produce two runs of the same testset (e.g., against two different models), then request a comparison between them, and confirm the result lists newly-passing, newly-failing, and still-failing questions without needing to manually cross-reference the two reports.

**Acceptance Scenarios**:

1. **Given** two persisted runs of the same testset, **When** a person compares them, **Then** the comparison lists every question whose match status changed between the two runs.
2. **Given** two persisted runs, **When** a person compares them, **Then** the comparison also states, for each run, which model/URL it used, so the person knows what caused any difference.
3. **Given** two runs made from testsets that are not the same set of questions, **When** a person compares them, **Then** the system tells them the runs aren't directly comparable rather than producing a misleading question-by-question diff.

---

### User Story 3 - Point a run at a different model or endpoint without touching code (Priority: P3)

A person wants to try the same testset against a different model, or a different LLM provider/endpoint, to see which one performs better, without editing source files or wiring up new environment variables by hand each time.

**Why this priority**: This makes the tool actually "easy" to use for comparison, as requested, but the underlying run/report mechanics (User Story 1) deliver value even if, for a first cut, selecting the target is a little more manual.

**Independent Test**: Start two runs of the same testset that only differ in the chosen model and/or URL, and confirm both runs complete and each one's report/summary clearly states which model and URL it used.

**Acceptance Scenarios**:

1. **Given** a person wants to test a specific model and endpoint, **When** they start a run, **Then** they can specify both without modifying any source file.
2. **Given** a run has completed, **When** a person looks at its report, **Then** the model and URL used for that run are recorded and visible.

---

### Edge Cases

- What happens when the testset file is missing, empty, or has a record missing a required field (question/expected)? The run should fail fast with a clear message rather than producing a partial, silently-incomplete report.
- What happens when the same question text appears twice in a testset (e.g., by mistake)? Each occurrence is treated as its own isolated question and reported separately.
- What happens when a run is interrupted partway (e.g., the process is killed)? Partial results already produced are not presented as if they were a complete run.
- What happens when the configured model/URL is unreachable for the entire run (not just one question)? The person is told clearly that the target could not be reached, rather than getting a report full of individually "errored" questions with no indication of the common cause.
- What happens when two runs being compared used different versions of the testset file (same name, different content)? The comparison must call this out rather than silently comparing mismatched questions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow a person to start a test run against a testset file structured like the bundled sample (`data/testsets/orcamentos-aeb-csv.json`): a list of questions, each with an identifier, question text, expected answer, source reference, and category.
- **FR-002**: System MUST allow a person to specify, per run, which model and which URL/endpoint the agent should use to answer questions, without editing source code.
- **FR-003**: System MUST ask each question in a run in isolation: no memory, conversation history, or other state may carry over from one question to another within the same run.
- **FR-004**: System MUST run every question in the testset even if answering an individual question fails or errors, recording the failure against that specific question instead of aborting the whole run.
- **FR-005**: For each question in a run, the system MUST capture and report: the question text, the expected answer, the agent's actual answer, the agent's own reported outcome (e.g., complete/partial/no answer), which dataset the agent selected, and the sequence of retrieval steps/tool actions the agent took to arrive at its answer.
- **FR-006**: Where a question's expected answer is a directly comparable value (e.g., a number), the system MUST automatically determine and clearly mark whether the agent's answer matches it.
- **FR-007**: Where a question's expected answer is not a directly comparable value (e.g., a qualitative statement), the system MUST flag the question for a person's own judgment instead of automatically marking it right or wrong.
- **FR-008**: System MUST produce, for each run, a summary showing the overall match rate and a per-question list of outcomes, so a person can immediately see which questions or categories are failing without reading the full per-question detail first.
- **FR-009**: System MUST persist every run's full results — per-question detail, summary, testset identity, and the model/URL used — so a run can be revisited and reused for comparison after the fact.
- **FR-010**: System MUST allow a person to compare two persisted runs of the same testset and see which questions changed match status between them (newly passing, newly failing, still failing, still passing).
- **FR-011**: System MUST record, for every run, which testset (including its version/content, not just its file name) and which target model/URL were used, and MUST warn rather than silently proceed if two runs being compared do not share the same set of questions.
- **FR-012**: System MUST support running the full bundled sample testset (`orcamentos-aeb-csv.json`, 50 questions across the categories present in that file) end-to-end as a single run.
- **FR-013**: System MUST fail a run clearly, before producing a misleading report, if the testset file is missing, unreadable, or contains a record missing a required field.

### Key Entities

- **Testset**: A named, versioned collection of Questions loaded from a file (e.g., `orcamentos-aeb-csv.json`); identified well enough that two testsets with the same name but different content are never treated as identical.
- **Question**: A single test item — an identifier, the question text (in Portuguese), the expected answer, a reference to where that answer comes from, and a category (e.g., single-lookup, calculation, multiple-files, edge-case).
- **Target Configuration**: The model and URL/endpoint the agent used to answer questions for a given run.
- **Test Run**: One execution of a Testset against a Target Configuration at a point in time; owns a Summary and one Question Result per Question.
- **Question Result**: The outcome of asking one Question within one Test Run — the agent's actual answer, its self-reported outcome, the dataset it selected, its step-by-step actions, and the match status against the expected answer (matched / not matched / needs review / errored).
- **Run Comparison**: A derived view over two Test Runs of the same Testset, showing which Questions changed match status between them.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A person can start a full run of the 50-question sample testset against a model and URL of their choice, and get back a complete report, without editing any source file.
- **SC-002**: For any not-matched or needs-review question in a run's report, a person can determine which dataset the agent used and how it arrived at its answer using only that report — no separate log inspection or re-run required.
- **SC-003**: Comparing two runs of the same testset surfaces every question with a changed match status; a person reviewing the comparison does not need to manually re-check any unchanged question to trust the comparison is complete.
- **SC-004**: Across a full run, no question's answer is affected by any other question asked in the same run (zero cross-question leakage).
- **SC-005**: A run's summary alone (without opening per-question detail) tells a person the overall match rate and which categories of question are underperforming.
- **SC-006**: Re-running the same testset against the same target configuration produces a report in the same structure and level of per-question detail every time, so runs stay comparable over time.

## Assumptions

- The bundled sample testset's schema (question identifier, question text, expected answer, source reference, category) is the schema all testsets follow; future testsets are just additional files in the same shape.
- "URL" refers to the LLM provider/endpoint the agent's model runs against (for example, a hosted API vs. a self-hosted or alternate-provider endpoint) — there is no existing deployed web service for this application to point at instead.
- Automatic match-checking only applies to expected answers that are plain comparable values (numbers, short exact strings); reasonable formatting differences (currency symbols, thousands separators, surrounding whitespace) are normalized before comparing. Anything else is routed to human review rather than auto-graded.
- Test runs are started manually by one person at a time for their own review; no multi-user access control, scheduling, or CI integration is required for this feature.
- The existing per-question application logs (dataset selection log, agent run log) are not sufficient on their own for this feature's reporting needs; this feature produces its own dedicated, self-contained run report.
- Testsets and runs are small enough (tens to low hundreds of questions) that a run completing fully before a person reviews it is an acceptable way of working; resuming a run from where it was interrupted is out of scope for this feature.
