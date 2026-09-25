# Feature Specification: Question-Answering Agent Workflow

**Feature Branch**: `003-qa-agent-workflow`

**Created**: 2026-09-18

**Status**: Draft

**Input**: User description: "Now we need to develop the actual agent workflow that will receive the question, use the data selector module to select the dataset to be used, and use the data access tools module to query the data and give the user a proper answer. The agent should never fabricate answers, when the dataset doesn't have the data the user is requesting, the agent should state that clearly. It should be considered that the user knows nothing about what dataset is being used and about it's structure. It should also be considered that the questions will always be asked in Portuguese and should always be answered in Portuguese."

## Clarifications

### Session 2026-09-18

- Q: What should the maximum number of retrieval steps be before the agent gives up on a question? (FR-012) → A: 10 steps
- Q: If the 10-step bound is reached after the agent already retrieved some (but not all) of the facts needed, should the final answer include those already-retrieved facts, or should it be a blanket failure message? → A: Present partial facts — treat it like the partial-answer case (FR-007), answering with whatever was actually retrieved and grounded, and explicitly stating the rest couldn't be completed within the step budget.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get a grounded answer to a covered question (Priority: P1)

A user asks a question, in Portuguese, about a topic the available data actually covers (e.g., how much was paid for a given budget action in a given year). The agent figures out on its own which dataset to consult and how to retrieve the relevant facts, then answers in Portuguese using only what it actually retrieved.

**Why this priority**: This is the entire point of the feature — turning a natural-language question into a correct, trustworthy answer without the user needing to know anything about datasets, files, or fields. Nothing else matters if this core path doesn't work.

**Independent Test**: Submit a Portuguese question whose answer is fully derivable from the sample dataset (e.g., "quanto foi pago pela AEB em 2015?") and confirm the response is in Portuguese, states a value that matches the underlying data, and requires no dataset/field knowledge from the user.

**Acceptance Scenarios**:

1. **Given** a Portuguese question about a fact the dataset covers, **When** the agent processes it, **Then** it selects the appropriate dataset, retrieves the matching data, and returns a Portuguese answer whose factual content (numbers, names) matches the underlying data exactly.
2. **Given** the same question phrased with an everyday synonym instead of the dataset's technical field name (e.g., "gasto" instead of "empenhado"), **When** the agent processes it, **Then** it still resolves the question to the correct underlying field and answers correctly.
3. **Given** a question whose answer requires reading only one value from the data, **When** the agent processes it, **Then** the final answer contains that value and does not surface internal details such as file names, column names, or dataset identifiers.

---

### User Story 2 - Clearly decline when the data doesn't cover the question (Priority: P2)

A user asks a question about something the available dataset does not contain — wrong subject, wrong time period, or a level of detail the data doesn't track. Instead of guessing or inventing a plausible-sounding number, the agent tells the user, in Portuguese, that it cannot answer with the data available.

**Why this priority**: Fabricated answers are worse than no answer for a data-driven agent; this is the safeguard that makes every other answer trustworthy. It's second only to the core answering path because it depends on the same retrieval flow to first determine coverage.

**Independent Test**: Submit a Portuguese question fully outside the sample dataset's documented coverage (e.g., about a different government agency, or a year outside its range) and confirm the response clearly states the data doesn't cover it, in Portuguese, with no fabricated figure.

**Acceptance Scenarios**:

1. **Given** a question about a subject the dataset's briefing explicitly does not cover (e.g., a different ministry), **When** the agent processes it, **Then** it responds in Portuguese stating plainly that the available data does not cover that subject, without producing any invented figure or fact.
2. **Given** a question about a time period outside the dataset's documented range, **When** the agent processes it, **Then** it responds in Portuguese stating the data doesn't cover that period, and does not extrapolate or estimate a value.
3. **Given** a question that asks for a level of detail the dataset doesn't track (e.g., a monthly or per-supplier breakdown when only yearly totals exist), **When** the agent processes it, **Then** it responds in Portuguese explaining that this level of detail isn't available, without approximating it from a coarser figure.
4. **Given** a question that is partly covered and partly not (e.g., asks for two facts, only one of which the dataset has), **When** the agent processes it, **Then** it answers the covered part and explicitly states, in Portuguese, which part it could not answer and why.

---

### User Story 3 - Answer questions that require multiple retrieval steps (Priority: P3)

A user asks a question that can't be answered by a single lookup — it requires first understanding the data's structure, then filtering or grouping it (e.g., "qual ação teve o maior valor pago em 2015?", which requires filtering by year and finding a maximum). The agent works through the necessary steps itself and returns one coherent final answer.

**Why this priority**: This is what makes the agent useful beyond trivial single-fact lookups, but it builds directly on the retrieval-and-grounding behavior established by User Stories 1 and 2, so it's ordered after them.

**Independent Test**: Submit a Portuguese question that requires combining a filter and an aggregate (e.g., a ranking or a grouped total) against the sample dataset, and confirm the agent performs the necessary underlying steps itself and returns a single correct Portuguese answer, without the user needing to break the question into steps.

**Acceptance Scenarios**:

1. **Given** a question requiring a filter followed by an aggregate computation (e.g., a total for a specific year and unit), **When** the agent processes it, **Then** it performs both steps itself and returns one final Portuguese answer with the correct computed value.
2. **Given** a question asking for a ranking or extreme value (e.g., "highest", "lowest"), **When** the agent processes it, **Then** it retrieves enough data to determine the correct answer and states it, rather than answering from a partial or unsorted sample.
3. **Given** a question requiring the agent to first learn the data's fields before it can filter correctly, **When** the agent processes it, **Then** it inspects the data's structure as part of its own process before issuing the filter, transparently to the user.

---

### User Story 4 - Translate technical failures into plain Portuguese (Priority: P4)

While trying to answer a question, an underlying step can fail for a technical reason (e.g., a referenced dataset can't be located, or a data source can't be parsed). The user still receives a clear, non-technical Portuguese explanation rather than a raw error or a silent wrong answer.

**Why this priority**: Lower priority because it's an edge-path safeguard rather than the main flow, but still required so failures never look like fabricated success or expose internal implementation details to a user who has no context for them.

**Independent Test**: Force an underlying retrieval failure (e.g., request a fact that requires an intentionally unreadable data source) and confirm the user-facing response is a plain-language Portuguese explanation with no raw technical error text, file paths, or internal identifiers.

**Acceptance Scenarios**:

1. **Given** an underlying data retrieval step fails with a technical error, **When** the agent composes its response, **Then** the user sees a plain Portuguese explanation that it could not complete the request, without raw error codes, stack traces, file paths, or internal field/table identifiers.
2. **Given** a technical failure occurs partway through a multi-step question, **When** the agent composes its response, **Then** it does not present a partial or guessed result as if it were complete and correct.

---

### Edge Cases

- What happens when a question is ambiguous between two dataset fields (e.g., a term that could plausibly map to either "empenhado" or "pago")? The agent must resolve it using the dataset's documented field meanings/synonyms and state which interpretation it used, rather than silently picking one or refusing to answer.
- What happens when a question mixes a covered and an uncovered aspect in one sentence? The agent answers the covered part and explicitly names what it couldn't answer (see User Story 2, Scenario 4).
- What happens when the question is too vague to map to any concrete data (e.g., "me fale sobre o orçamento")? The agent treats this the same as an uncoverable question and states, in Portuguese, that it needs a more specific question to look up a fact, rather than guessing what was meant.
- What happens when the underlying dataset selection or retrieval steps take more attempts than the 10-step bound allows? If no facts were successfully retrieved before the bound was reached, the agent stops and reports, in Portuguese, that it could not determine an answer, rather than looping indefinitely. If some facts were already retrieved and grounded before the bound was reached, the agent answers with those facts and explicitly states, in Portuguese, that the remainder could not be completed within the step budget (the same partial-answer treatment as User Story 2, Scenario 4).
- What happens when the same question is asked twice? Each request is handled independently and produces its own answer and its own usage record.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a user's question as Portuguese natural-language text and produce a final answer as Portuguese natural-language text, for every request.
- **FR-002**: System MUST determine which dataset applies to a question by invoking the dataset selection capability before attempting any data retrieval, and MUST use the briefing and data location it returns to guide the rest of the request.
- **FR-003**: System MUST use the selected dataset's briefing to interpret the question in terms of the dataset's actual fields and structure, so that the user is never required to know or name any technical schema detail (file names, column names, identifiers) to be understood.
- **FR-004**: System MUST retrieve every fact used in an answer via the data access capabilities (discovery, schema inspection, filtered query, aggregation) rather than presenting a value that was not actually retrieved during that request.
- **FR-005**: System MUST NOT include in a final answer any number, name, or fact that was not obtained from a data access retrieval performed during that same request; general/outside knowledge MUST NOT be used to fill in factual content about the dataset's subject matter.
- **FR-006**: When the selected dataset does not contain the information needed to answer a question (wrong subject, out-of-range time period, or a granularity the data doesn't track), system MUST respond with a clear Portuguese statement that the available data does not cover the question, and MUST NOT produce an approximated, extrapolated, or guessed value instead.
- **FR-007**: When a question is only partially answerable, system MUST answer the part it can support with retrieved data and MUST explicitly state, in Portuguese, which part it could not answer and why.
- **FR-008**: When answering a question requires more than one retrieval step (e.g., inspecting structure, then filtering, then aggregating), system MUST perform the necessary sequence of steps itself, using each step's result to decide the next, without requiring the user to decompose the question.
- **FR-009**: When a dataset-selection or data-access step fails for a technical reason (e.g., unreadable source, not-found identifier, invalid field reference), system MUST translate that failure into a plain, non-technical Portuguese explanation in the final answer, and MUST NOT expose raw error text, file paths, or internal identifiers as the user-facing explanation.
- **FR-010**: When a question is ambiguous with respect to which dataset field or metric it refers to, system MUST resolve the ambiguity using the dataset briefing's documented field meanings and synonyms, and MUST state, as part of the answer, which interpretation it used.
- **FR-011**: System MUST treat every question as an independent request, answered using only the information gathered while handling that request, without depending on hidden state carried over from a previous, separate question.
  - *Note (008)*: [008-chat-conversation-history](../008-chat-conversation-history/spec.md) adds a separate conversational path (`answer_turn`), used only by the web UI chat and the conversation runner, that passes the earlier visible turns of the same chat as context. This single-question contract (`answer_question`) stays in force everywhere else, unchanged.
- **FR-012**: System MUST bound the number of retrieval steps it will attempt while answering a single question to at most 10 steps, rather than continuing to retry indefinitely once that bound is reached. If the bound is reached with no facts successfully retrieved, system MUST report an inability to answer, in Portuguese. If the bound is reached after some facts were already retrieved and grounded, system MUST apply the same partial-answer treatment as FR-007 — answering with the retrieved facts and explicitly stating, in Portuguese, that the remainder could not be completed within the step budget.
- **FR-013**: System MUST record, for each question processed, at least the question, the dataset used, whether it was answered fully, partially, or not at all, and a timestamp, as usage/research data.

### Key Entities

- **Question**: The user's natural-language request, always submitted in Portuguese.
- **Final Answer**: The natural-language Portuguese response returned to the user — either a grounded factual answer, a partial answer with an explicit gap statement, or an explicit "cannot answer with the available data" statement.
- **Retrieval Step**: One invocation of a data access capability (discovery, schema inspection, filtered query, or aggregation) made while working out an answer, together with its result; a single question may involve one or several retrieval steps.
- **Answerability Outcome**: The agent's determination, based on what was actually retrieved, of whether a question was fully answered, partially answered, or not answerable with the selected dataset.
- **Agent Run Log Entry**: A recorded observation of one question-answering request — the question, the dataset selected, the answerability outcome, and a timestamp — kept as usage/research data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For questions whose answer is within the selected dataset's documented coverage, the final answer's factual content (numbers, names) matches the underlying data exactly, on 100% of a representative set of test questions.
- **SC-002**: For questions outside the selected dataset's documented coverage, 0% of responses present a fabricated, guessed, or extrapolated figure; 100% clearly state, in Portuguese, that the data doesn't cover the question.
- **SC-003**: 100% of final answers are delivered in Portuguese, regardless of the underlying dataset's field names or internal terminology.
- **SC-004**: 100% of final answers' factual content can be traced to at least one retrieval step actually performed during that same request.
- **SC-005**: A representative set of test questions requiring multiple retrieval steps (filter plus aggregate, or ranking) are answered correctly without the user needing to split the question into sub-questions, in at least 90% of cases.
- **SC-006**: 100% of responses triggered by an underlying technical failure are delivered as a plain Portuguese explanation, with zero raw error text, file paths, or internal identifiers surfaced to the user.
- **SC-007**: A user with no prior knowledge of the dataset's existence, name, or structure can obtain a correct answer to a covered question using only their own natural-language Portuguese question.

## Assumptions

- Each question is handled as a single, self-contained request-and-response exchange; carrying conversational context or follow-up references across separate questions (e.g., "e em 2015?" referring to a prior question) is out of scope for this feature.
  - *Note (008)*: conversational context is added by [008-chat-conversation-history](../008-chat-conversation-history/spec.md) as a separate path for the web UI and the conversation runner; this feature's single-question contract is unchanged.
- Questions are assumed to already be well-formed Portuguese text; detecting, rejecting, or translating non-Portuguese input is out of scope.
- This feature depends on and reuses the existing dataset selection module exactly as it behaves today (currently always returning the single registered `orcamentos-aeb-csv` dataset); any future change to selection logic (e.g., choosing among multiple datasets) is transparent to this feature and requires no change to how it issues its request.
- This feature depends on and reuses the existing data access tool layer's four capabilities (discovery, schema inspection, filtered query, aggregation) exactly as they behave today; it introduces no new data-retrieval capability of its own, only the orchestration and Portuguese-language framing of existing ones.
- The bound on retrieval steps per question (FR-012) is a fixed value (10 steps) for this initial contract rather than something the user can configure per question.
- The agent run log (FR-013) is written once per question, at the point a final answer — positive, partial, or "cannot answer" — is produced, and is separate from (and in addition to) the dataset-selection log entry already produced by the dataset selection module.
- "Fabrication" means presenting any factual content (a number, a name, a comparison) that was not obtained from an actual retrieval step performed during that request; reasonable connective/explanatory language in the answer (e.g., restating the question, describing what was checked) is not considered fabrication.
