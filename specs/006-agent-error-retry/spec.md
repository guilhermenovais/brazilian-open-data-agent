# Feature Specification: Agent Error Details and Bounded Retry

**Feature Branch**: `006-agent-error-retry`

**Created**: 2026-09-24

**Status**: Draft

**Input**: User description: "We need to make some improvements to this application that will impact the testset run evaluations. First, when there is an exception on the agent run, it's type and message should be recorded. Second, we should have a bounded retry for transient failures."

## Context

Today, when answering a question fails unexpectedly during an agent run (for example, the model provider times out, rate-limits the request, or returns a server error), the failure is swallowed: the question is marked as "errored" in the testset run report, but nothing records *what* went wrong. A person reviewing the run cannot tell a one-off network hiccup from a misconfigured model name, an authentication problem, or a bug in the application. And because a single transient hiccup is enough to mark a question as errored, the run's match rate can drop for reasons unrelated to the agent's actual ability to answer, making runs less comparable over time.

This feature addresses both problems: errored questions carry the failure's type and message, and failures that are likely to succeed on a second try are retried a limited number of times before a question is given up on.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See why a question errored (Priority: P1)

A person reviewing a completed testset run sees that some questions are marked "errored". For each one, the report shows the kind of failure that occurred (its type) and the failure's message, so the person can tell immediately whether the cause was, say, a timeout, a rate limit, an invalid model name, or an authentication problem — without re-running the question or digging through separate application logs.

**Why this priority**: Without the failure details, an "errored" result is a dead end: the person cannot act on it. This is also a prerequisite for trusting the retry behavior in User Story 2, since it shows which failures happened and whether they were retried. It delivers value on its own even with no retry at all.

**Independent Test**: Run a testset against a target configured so that the agent run fails (e.g., an unreachable endpoint or an invalid model name), then open the run report and confirm each errored question shows a failure type and message that identifies the cause.

**Acceptance Scenarios**:

1. **Given** a testset run in which the agent run fails for a question, **When** a person views that question in the run report, **Then** it is marked "errored" and shows the failure's type and message.
2. **Given** a testset run in which a question is answered normally (matched, not matched, or needs review), **When** a person views that question, **Then** no failure details are shown for it.
3. **Given** a run in which every question errored for the same cause (e.g., the endpoint is unreachable), **When** a person reads the run summary, **Then** they can see the common failure type(s) and how many questions each affected, without opening each question.
4. **Given** a failure whose message contains a credential (e.g., an API key echoed back by the provider), **When** the failure is recorded, **Then** the credential does not appear in the persisted run or any log.
5. **Given** a question that errored before reaching the model (e.g., dataset selection failed), **When** a person views it, **Then** it also shows a failure type and message describing that failure.

---

### User Story 2 - Transient failures don't count against the agent (Priority: P2)

A person runs a testset against a model provider that occasionally times out, rate-limits, or returns a temporary server error. Instead of those questions being marked errored on the first hiccup, the system tries the question again a limited number of times, waiting a little longer between each try. If a retry succeeds, the question is graded normally. If all tries fail, the question is marked errored with the last failure's details. Failures that will not go away by retrying (such as an invalid credential or an unknown model) are not retried, so the run doesn't waste time and fails fast on them.

**Why this priority**: This makes match rates reflect the agent's ability to answer rather than momentary provider instability, keeping runs comparable. It builds on User Story 1, since failure details are what let a person verify retries behaved correctly.

**Independent Test**: Run a testset against a target that fails transiently for the first attempt of some questions and then succeeds (e.g., a simulated flaky provider), and confirm those questions are graded normally and the report shows they needed more than one attempt; then run against a target that fails permanently (e.g., invalid credential) and confirm each question is attempted only once.

**Acceptance Scenarios**:

1. **Given** a question whose first attempt fails with a transient failure and whose second attempt succeeds, **When** the run completes, **Then** the question is graded on the successful attempt's answer and the report shows it took 2 attempts, including the first attempt's failure type and message.
2. **Given** a question that fails with a transient failure on every attempt, **When** the retry limit is reached, **Then** no further attempts are made, the question is marked errored, and the report shows the number of attempts made and each attempt's failure type and message.
3. **Given** a question that fails with a non-transient failure (e.g., authentication rejected, unknown model, invalid request), **When** that failure occurs, **Then** the question is not retried and is marked errored after a single attempt.
4. **Given** a retried question, **When** it is attempted again, **Then** the new attempt starts fresh, with nothing from the failed attempt (partial steps, conversation, intermediate results) carried over, and the reported steps reflect only the attempt whose outcome is graded.
5. **Given** a completed run, **When** a person reads its summary, **Then** it shows how many questions needed a retry and how many were ultimately errored despite retries.

---

### User Story 3 - Control and record the retry policy (Priority: P3)

A person wants to change how many attempts are allowed (for example, disable retries entirely to see the raw failure rate of a provider, or allow more attempts against a known-flaky endpoint) without editing source code. Whatever policy was used is recorded with the run, so two runs with different retry policies are never mistaken for identical conditions.

**Why this priority**: A sensible default makes User Story 2 useful out of the box; being able to change and record the policy is what keeps runs reproducible and comparable, but is less urgent than the retry behavior itself.

**Independent Test**: Start two runs of the same testset with different maximum-attempt settings (including retries disabled), and confirm each run respects its setting and records it in its persisted results; then compare the two runs and confirm the difference in retry policy is shown.

**Acceptance Scenarios**:

1. **Given** a person starts a run and specifies a maximum number of attempts, **When** transient failures occur, **Then** no question is attempted more than that number of times.
2. **Given** a person sets the maximum number of attempts to 1, **When** a transient failure occurs, **Then** the question is not retried.
3. **Given** a completed run, **When** a person views its persisted results, **Then** the retry policy used for the run is recorded alongside the model and URL.
4. **Given** two runs with different retry policies, **When** a person compares them, **Then** the comparison states each run's retry policy.

---

### Edge Cases

- A failure has an empty message: the type is still recorded, and the message is recorded as empty rather than omitted or replaced with a misleading placeholder.
- A failure has a very long message (e.g., a full provider error body): the recorded message is shortened to a bounded length with a clear truncation marker, so a single failure can't bloat the report.
- A failure wraps another failure (e.g., a generic error caused by a timeout): the recorded details identify the underlying cause, not just the outer wrapper, so the transient/non-transient decision and the report both reflect the real cause.
- A failure's classification is unknown (not recognizably transient or non-transient): it is treated as non-transient and not retried, so unexpected bugs surface immediately instead of being masked by retries.
- The agent exhausts its own retrieval step budget or produces an unusable answer: this is an agent-behavior outcome, not a transient infrastructure failure, and is not retried.
- The provider asks the client to wait a specific amount of time before retrying (e.g., a rate-limit response with a suggested delay): the wait before the next attempt respects that suggestion, within an upper bound so a single question can't stall the run indefinitely.
- The target is unreachable for the whole run: each question stops after its bounded attempts, the run completes, and the summary's "target unreachable" indication is still shown, now together with the common failure type.
- A run persisted before this feature (no failure details, no attempt counts, no retry policy) is opened or compared: it still loads and compares, with those fields shown as not recorded rather than causing an error.
- The run is interrupted during a wait between attempts: behavior matches any other interrupted run — partial results are not presented as a complete run.

## Requirements *(mandatory)*

### Functional Requirements

**Failure details**

- **FR-001**: When answering a question fails unexpectedly during a testset run, the system MUST record the failure's type and message against that question.
- **FR-002**: The system MUST show the recorded failure type and message for every errored question in the run report, and MUST NOT show failure details for questions that were answered normally.
- **FR-003**: The system MUST record failure details for errors at any stage of answering a question, including failures before the model is reached (e.g., dataset selection) and failures during the agent run.
- **FR-004**: Where a failure was caused by an underlying failure, the recorded details MUST identify the underlying (root) cause's type and message.
- **FR-005**: The system MUST remove credentials (such as API keys or authorization tokens) from recorded failure messages before they are persisted or logged.
- **FR-006**: The system MUST cap the length of a recorded failure message, marking clearly when it has been shortened.
- **FR-007**: The run summary MUST show, for errored questions, a count of questions per failure type.
- **FR-008**: The per-question application run log MUST also record the failure type and message for errored agent runs, so that usage data captured outside testset runs carries the same information.
- **FR-009**: The answer shown to an end user (the agent's user-facing answer text) MUST NOT change as a result of this feature; failure details are recorded for review, not exposed in the answer itself.

**Bounded retry**

- **FR-010**: The system MUST classify each failure as transient (likely to succeed if tried again) or non-transient. At minimum, transient failures include: request timeouts, connection failures, rate-limit responses, and temporary server-side errors from the model provider. Non-transient failures include: authentication/authorization rejections, unknown model, invalid request, and dataset selection failures.
- **FR-011**: Failures that cannot be classified MUST be treated as non-transient.
- **FR-012**: When a question fails with a transient failure, the system MUST attempt it again, up to a maximum total number of attempts per question.
- **FR-013**: The system MUST NOT retry a question after a non-transient failure.
- **FR-014**: The system MUST wait before each retry, with the wait increasing on successive retries; when the provider indicates how long to wait, the system MUST respect that indication, subject to an upper bound on any single wait.
- **FR-015**: Each retry MUST start the question fresh, with no conversation, partial steps, or intermediate results carried over from a failed attempt, preserving the existing per-question isolation guarantee.
- **FR-016**: If a retry succeeds, the question MUST be graded on that attempt's answer, and its reported steps MUST be those of that attempt.
- **FR-017**: If every allowed attempt fails, the question MUST be marked errored with the final attempt's failure details, and the run MUST continue with the next question.
- **FR-018**: For each question, the system MUST record the number of attempts made and the failure type and message of every failed attempt, including failed attempts that preceded a successful one.
- **FR-019**: The run summary MUST show how many questions needed more than one attempt and how many remained errored after exhausting their attempts.

**Retry policy configuration and reproducibility**

- **FR-020**: A person MUST be able to set the maximum number of attempts per question for a run without editing source code; setting it to 1 disables retries.
- **FR-021**: Absent an explicit setting, the system MUST use a default of 3 total attempts per question (the first attempt plus up to 2 retries).
- **FR-022**: The retry policy used for a run MUST be persisted with the run alongside its target model and URL.
- **FR-023**: When two runs are compared, the comparison MUST state each run's retry policy.
- **FR-024**: Runs persisted before this feature MUST remain loadable and comparable; missing failure details, attempt counts, and retry policy MUST be presented as "not recorded".

### Key Entities

- **Failure Detail**: A description of one failure: its type, its (credential-free, length-capped) message, and whether it was classified as transient.
- **Attempt**: One try at answering a question within a test run; either succeeds (producing an answer to grade) or fails with a Failure Detail.
- **Question Result** *(extended)*: In addition to its existing fields, records the number of attempts made, the Failure Detail of each failed attempt, and — when errored — the final Failure Detail.
- **Retry Policy**: The rules applied to a run: maximum attempts per question and the waiting behavior between attempts. Recorded as part of the run's configuration.
- **Run Summary** *(extended)*: In addition to its existing figures, the count of errored questions per failure type, the count of questions that needed a retry, and the count that remained errored after all attempts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For 100% of errored questions in a run report, a person can identify the failure's type and message from the report alone, without consulting separate logs or re-running the question.
- **SC-002**: In a run where every question fails on its first attempt with a transient failure and succeeds on its second, zero questions are reported as errored and every question shows 2 attempts.
- **SC-003**: No question is ever attempted more times than the run's configured maximum, and questions failing non-transiently are attempted exactly once.
- **SC-004**: No credential supplied to the run appears anywhere in a persisted run or log, even when the provider echoes it back in a failure message.
- **SC-005**: A run whose target is fully unreachable, with the default retry policy, still completes and reports the common failure cause in its summary, taking no longer than the configured attempts and bounded waits allow per question.
- **SC-006**: Every run persisted before this feature can still be opened and compared against a new run without errors.

## Assumptions

- "Agent run" covers everything involved in answering one question within a testset run — dataset selection and the model/tool-calling loop — since both can leave a question "errored" today. Retrying, however, targets the transient failures that occur when talking to the model provider; dataset selection failures are local and deterministic and are not retried.
- The primary consumer of this feature is the testset runner and its reports. The chat web UI shares the same answering component; it benefits from recorded failure details in the application run log (FR-008), but no change to its user-facing behavior or display is in scope.
- A retry re-asks the whole question from scratch rather than resuming mid-conversation. This costs some extra model usage per retried question but keeps the existing isolation guarantee and makes the graded attempt self-contained.
- The default of 3 total attempts, with a short, increasing wait (on the order of seconds) and a per-wait upper bound (on the order of a minute), is a common industry default for calls to hosted model providers and keeps a fully unreachable run's duration bounded.
- The run comparison continues to compare match status only; differences in attempt counts or failure types between two runs are shown as information, not treated as a change in match status.
- The model provider's failures carry enough information (e.g., a status indication or a recognizable failure kind) to classify the common transient cases in FR-010; anything else falls back to non-transient per FR-011.
