# Feature Specification: Conversational Context in the Web UI Chat

**Feature Branch**: `008-chat-conversation-history`

**Created**: 2026-09-25

**Status**: Draft

**Input**: User description: "On the Web UI, in a chat instance I want the agent to keep the conversation history, allowing the user to ask follow up questions and to clarify when the agent asks for clarification"

## Context

Today the web UI *shows* the full conversation, but the agent only ever receives the latest question. Every question is answered as if it were the first. This comes from the original agent workflow spec (003, FR-011 and its first Assumption), which kept follow-up references out of scope. So a user who asks "quanto foi pago pela AEB em 2015?" and then "e em 2016?" gets a reply saying the second question is too vague. A user who answers the agent's request for a more specific question gets the same result, because the agent has no record of what it asked.

This feature lets the agent understand a message in the context of the earlier messages in the same chat. It applies to web UI conversations and to the runner that replays scripted conversations for evaluation (FR-015). Standalone batch entry points such as the testset runner keep answering each question on its own.

## Clarifications

### Session 2026-09-25

- Q: Should the agent see only the visible text of earlier turns, or also their data retrievals (tool calls and results)? → A: Visible text only: earlier user messages and the agent's final replies.
- Q: Should this feature include a repeatable, automated way to run and score scripted multi-turn conversations (SC-001 to SC-005)? → A: Yes. Add a scripted conversation test set and a runner mode that replays it turn by turn and scores each turn, separate from the standalone testset runner.
- Q: How should the system decide a conversation is too long and start dropping the oldest turns? → A: By size. It keeps as many of the most recent whole turns as fit within a configurable history size limit and drops the oldest first.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask a follow-up question that depends on earlier turns (Priority: P1)

A user asks a question in Portuguese and gets an answer. They then send a short follow-up that only makes sense with the earlier exchange, such as "e em 2016?", "e o empenhado?", "qual foi a maior delas?" or "compare com o ano anterior". The agent uses the earlier turns to work out what the follow-up means and answers it as if the user had written out the full question.

**Why this priority**: This is the main value of the feature. People exploring data in a chat naturally ask a series of related questions, and having to restate the full context each time is the biggest usability gap in the web UI today.

**Independent Test**: In a new chat, ask "quanto foi pago pela AEB em 2015?", then "e em 2016?". The second answer should give the paid amount for 2016, match the underlying data, and require no restating of the subject or metric.

**Acceptance Scenarios**:

1. **Given** a chat in which the agent has answered a question about a metric for one year, **When** the user asks a follow-up that changes only the year (e.g., "e em 2016?"), **Then** the agent answers for the same subject and metric in the new year, and the value matches the underlying data.
2. **Given** a chat in which the agent has answered a question, **When** the user asks a follow-up that changes only the metric (e.g., "e quanto foi empenhado?"), **Then** the agent keeps the subject and period from the earlier turn and answers for the new metric.
3. **Given** a chat in which the agent listed several items (e.g., the actions with the highest paid amount), **When** the user refers back to them (e.g., "qual dessas teve o menor valor empenhado?"), **Then** the agent works out which items are meant and answers about those items.
4. **Given** a chat in which the agent has answered a question, **When** the user asks a new question that is complete on its own and unrelated to the earlier turns, **Then** the agent answers it on its own terms and does not carry over earlier filters or subjects the new question does not ask for.
5. **Given** a follow-up that could reasonably refer to more than one earlier item, **When** the agent answers, **Then** it says which earlier item it took the follow-up to refer to, following the same rule the agent already uses for ambiguous fields.

---

### User Story 2 - Answer the agent's request for clarification (Priority: P1)

The agent sometimes replies to a vague or underspecified question by asking the user to be more specific (e.g., for "me fale sobre o orçamento", it explains that it needs a more specific question). The user replies with only the missing detail (e.g., "o valor pago em 2015"). The agent combines that reply with the original question and answers the completed question.

**Why this priority**: The agent's clarification requests are useless in a chat if it can't connect the answer to the question it asked. This is the second behavior the user asked for explicitly, and it relies on the same conversation context as User Story 1.

**Independent Test**: In a new chat, send a question vague enough that the agent asks for more detail. Then send only the missing detail. The agent should answer the combined question and not treat the reply as a new, incomplete question.

**Acceptance Scenarios**:

1. **Given** the agent's last reply asked the user to clarify or narrow a question, **When** the user replies with only the missing information, **Then** the agent treats the original question and the reply together as one complete question and answers it.
2. **Given** the agent asked for clarification, **When** the user's reply still leaves the question underspecified, **Then** the agent asks again for what is still missing and does not guess.
3. **Given** the agent asked for clarification, **When** the user ignores the request and asks a different, complete question, **Then** the agent answers the new question and does not force it into the earlier, unfinished one.

---

### User Story 3 - Start a fresh conversation without leftover context (Priority: P2)

A user who has finished one line of inquiry starts a new chat. The new chat has no context from any earlier chat, so the agent reads its first question fresh.

**Why this priority**: Users need an easy, predictable way to reset context so an old topic can't quietly change how new questions are read. It matters less than the context-aware behavior itself.

**Independent Test**: Hold a conversation about one year. Start a new chat and ask "e em 2016?". The agent should say the question is too vague to answer, as it does today, and should not answer with the earlier chat's subject.

**Acceptance Scenarios**:

1. **Given** a user has had a conversation in one chat, **When** they start a new chat and ask a follow-up-style question, **Then** the agent has no context from the earlier chat and handles the question as a standalone question.
2. **Given** two chats open at the same time (e.g., two browser tabs), **When** the user asks follow-ups in each, **Then** each chat uses only its own history.

---

### Edge Cases

- **A follow-up depends on an earlier answer that failed or was declined** (e.g., the earlier turn got a technical-failure message or "the data doesn't cover this"). The agent must not treat the failure message as a fact. It may use the earlier *question* to understand the follow-up, but must retrieve every fact it states in the current turn.
- **The earlier turn's answer included a value, and the follow-up asks about the same value again** (e.g., "confirme o valor de 2015"). Facts stated in a new answer must be retrieved during the current turn, not copied from earlier answers in the conversation (see FR-005).
- **The conversation grows very long.** The chat must keep working. When the history exceeds the configured size limit, the oldest whole turns are dropped from the agent's context first, and the turn is still answered instead of failing (FR-011).
- **The user edits or regenerates an earlier message in the UI.** The agent uses the conversation exactly as the chat shows it at the time the new message is sent. Discarded versions of messages are not included.
- **An earlier turn used many retrieval steps.** The retrieval-step budget applies to each turn. Steps used in earlier turns do not count against the current turn's budget.
- **A follow-up changes the subject to something the dataset doesn't cover** (e.g., "e para o Ministério da Saúde?"). The agent declines as it would for the standalone question and does not answer from the earlier subject instead.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When the user sends a message in a web UI chat, the system MUST give the agent that chat's earlier user messages and the agent's final replies, in order, together with the new message. Only this visible text is passed. Data retrievals from earlier turns (tool calls and their results) MUST NOT be included.
- **FR-002**: The agent MUST use the earlier turns to interpret a follow-up that refers to them implicitly. This covers a changed year, metric or subject, and references such as "dessas", "o anterior" or "e em …". The agent then answers the question as the user meant it.
- **FR-003**: When the agent's previous reply asked the user for clarification or more detail, the agent MUST read the user's next message as a possible answer to that request. If it is, the agent MUST combine it with the original question before answering.
- **FR-004**: When a new message is a complete question that does not depend on earlier turns, the agent MUST NOT carry over subjects, filters, periods or metrics that the new question does not ask for.
- **FR-005**: Earlier turns may be used only to *interpret* the current message. Every number, name or fact in the current answer MUST come from a data retrieval performed during the current turn, as required by the existing no-fabrication rule (003 FR-004/FR-005). Values in earlier answers MUST NOT be repeated as facts without being retrieved again.
- **FR-006**: When a follow-up could plausibly refer to more than one earlier item, the agent MUST choose the most reasonable reading and say which one it used, in line with the existing ambiguity rule (003 FR-010).
- **FR-007**: Each chat MUST have its own history. Messages from one chat MUST NOT affect answers in another chat, including another chat open at the same time.
- **FR-008**: Starting a new chat MUST start with no earlier context.
- **FR-009**: Each turn MUST have its own retrieval-step budget of the size set for a single question (003 FR-012). Steps used in earlier turns MUST NOT reduce it.
- **FR-010**: The agent's context for a turn MUST follow the conversation as the chat currently shows it. Messages that were edited or regenerated MUST be used in their current form, and discarded versions MUST NOT be included.
- **FR-011**: The history given to the agent MUST fit within a history size limit. The limit MUST be set in the run configuration and recorded with each run. When the full history exceeds the limit, the system MUST keep as many of the most recent turns as fit and drop the oldest first. Turns are kept or dropped whole, never cut partway. The new message is always included, and the turn MUST still be answered. The default limit MUST fit at least 20 typical turns (SC-006).
- **FR-012**: All existing answer rules MUST still apply to every turn of a conversation: Portuguese-only answers, no internal file, column or identifier names, plain-language failure messages, and the full / partial / none outcome classification.
- **FR-013**: The usage record for each turn MUST store, alongside the fields it already has, the chat the turn belongs to and the turn's position in that chat. This lets follow-up and clarification exchanges be reconstructed and analysed as research data (Constitution Principle X).
- **FR-014**: Entry points that answer standalone questions, such as the testset runner, MUST keep answering each question with no conversation context. Their results for a given question and configuration MUST be the same as before this feature.
- **FR-015**: The system MUST provide a reproducible way to evaluate multi-turn conversations. It MUST include a scripted conversation test set covering follow-ups (changed year, changed metric, reference to listed items), clarification exchanges, standalone questions after unrelated turns, and follow-up-style first messages in a new chat. It MUST also include a runner mode that replays each scripted conversation turn by turn through the same conversational path the web UI uses, scores each scored turn against its expected answer, and records the run's inputs, configuration and per-turn results (Constitution Principle I). This mode MUST be separate from the standalone testset runner and MUST NOT change that runner's behavior (FR-014).

### Key Entities

- **Conversation**: One web UI chat. It is the ordered list of turns the user can see in that chat and is isolated from every other chat.
- **Turn**: One user message and the agent's reply to it. The reply is an answer, a partial answer, a decline, a clarification request or a failure message. It records the outcome classification and its position in the conversation.
- **Clarification Request**: An agent reply that asks the user for missing information instead of answering. The user's next message may complete the question it refers to.
- **Turn Usage Record**: The existing per-question usage record, extended with the conversation it belongs to and the turn's position in it.
- **Scripted Conversation**: An evaluation case made of an ordered list of user messages. Each scored turn has an expected answer. It is the multi-turn counterpart of a standalone testset question.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the scripted conversation test set (FR-015), for its two-turn follow-up conversations over the sample dataset (changed year, changed metric, reference to listed items), at least 90% of follow-up answers are correct and match the underlying data, without the user restating earlier context.
- **SC-002**: On the scripted conversation test set's clarification exchanges (vague question, agent asks for detail, user sends only the missing detail), at least 90% of the user's replies produce a correct answer to the completed question.
- **SC-003**: Across all scripted multi-turn conversations, 0% of answers state a figure that was not retrieved during that same turn. This is measured by the runner's automated figure-grounding check. Every figure it flags gets a recorded verdict: either derived deterministically from values retrieved in that turn, or ungrounded. The verdict and its reason are recorded with the run id so it can be re-verified from the saved run. The criterion is met when no flagged figure is ungrounded.
- **SC-004**: On the scripted conversation test set's standalone questions asked after unrelated earlier turns, 100% of answers are unaffected by the earlier turns: no leftover filters, years or subjects.
- **SC-005**: A follow-up-style question asked as the first message of a new chat never draws on another chat's content (0 occurrences across the scripted conversation test set).
- **SC-006**: A conversation of at least 20 turns stays usable. Every turn gets an answer, and no turn fails because of the conversation's length.
- **SC-007**: For the same question and configuration, the testset runner's results are the same before and after this feature.

## Assumptions

- The scope is the web UI chat, plus the conversation evaluation runner that replays scripted conversations through the same path (FR-015). The single-question contract (003 FR-011) stays in force for every other entry point, and this feature adds a conversational path next to it rather than replacing it.
- History is kept only for the life of the chat as the web UI already holds it. Storing conversations on the server or across restarts is out of scope. Operators still get the existing run log, extended as described in FR-013.
- The agent's existing ways of asking for clarification (e.g., asking for a more specific question when a question is too vague) are what users reply to. Changing *when* the agent asks for clarification is out of scope. In particular, the current rule of choosing and stating the most reasonable reading of an ambiguous field is unchanged.
- The rule that facts are retrieved again on every turn (FR-005) is deliberately strict. It keeps every answer traceable to retrievals from its own turn (003 SC-004), at the cost of repeating some queries. Relaxing it would need its own evidence and spec.
- Dataset selection still runs deterministically on every turn. There is only one registered dataset today, so selection does not depend on context. Making selection itself use conversation context, for when several datasets exist, is out of scope and left to a future spec.
- The web UI is an operator-facing local tool (005 Assumptions). History sent by the browser is trusted the same way the current question is, and no extra tamper-protection is required.
- Clarification requests are recognised from the conversation content itself. No separate "clarification" outcome is added to the full / partial / none classification.
