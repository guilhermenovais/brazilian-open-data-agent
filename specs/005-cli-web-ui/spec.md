# Feature Specification: CLI Web UI Launcher

**Feature Branch**: `005-cli-web-ui`

**Created**: 2026-09-22

**Status**: Draft

**Input**: User description: "I want to provide an easy way to run this project from the command line, with parameters to configure the model, url, key, etc. The app should expose Pydantic-ai Web UI (https://pydantic.dev/docs/ai/guides/web/)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start a chat session with one command (Priority: P1)

A person who has the project installed wants to ask questions of the agent without writing any code or wiring up scripts. They run a single command from their terminal and get a web-based chat interface they can open in a browser to type questions and read answers.

**Why this priority**: This is the core value of the feature — today the agent can only be exercised through test scripts and the testset runner. Without this, there is no way for a non-developer (or a developer in a hurry) to just talk to the agent.

**Independent Test**: Run the launch command with a valid model configured, open the printed URL in a browser, submit a question, and confirm an answer is displayed in the chat.

**Acceptance Scenarios**:

1. **Given** the project is installed and a model is configured, **When** the user runs the launch command, **Then** a local web server starts and the terminal prints a URL the user can open to reach the chat interface.
2. **Given** the web UI is open in a browser, **When** the user types a question and submits it, **Then** the interface shows the agent's answer in the conversation, consistent with the answers the agent produces through its other entry points.
3. **Given** the web UI is open, **When** the user asks a follow-up question in the same session, **Then** the conversation history for that session is visible alongside the new answer.

---

### User Story 2 - Configure model, endpoint, and credentials without editing code (Priority: P1)

A user wants to point the agent at a specific model, a specific API endpoint (e.g., a self-hosted or alternate provider endpoint), and supply the credential needed to call it — without modifying source files, and without permanently exporting environment variables if they don't want to.

**Why this priority**: The project already supports configuring model/base URL/API key for other entry points (the testset runner). The web UI must offer the same flexibility, or it becomes a second, inconsistent configuration surface — this is core to "an easy way to run this project."

**Independent Test**: Launch the command with explicit model, base URL, and API key flags pointing at a reachable target, and confirm the resulting chat session uses that target (e.g., by pointing at a different model and observing the behavior/identity change, or by checking the target is rejected clearly when unreachable).

**Acceptance Scenarios**:

1. **Given** no prior environment configuration, **When** the user runs the launch command with model, base URL, and API key passed as flags, **Then** the web UI starts and uses exactly that configuration for answering questions.
2. **Given** the relevant environment variables are already set in the shell, **When** the user runs the launch command with no flags, **Then** the web UI starts using the environment-provided configuration.
3. **Given** both a flag and an environment variable are set for the same setting, **When** the user runs the launch command, **Then** the flag value takes precedence.
4. **Given** no model is available from either a flag or an environment variable, **When** the user runs the launch command, **Then** the command fails immediately with a clear error message and does not start a server.

---

### User Story 3 - Choose where the web UI listens (Priority: P3)

A user wants to control which network interface and port the web UI binds to, so they can avoid clashing with another local service or, deliberately, make it reachable from another machine (e.g., a container or remote dev box).

**Why this priority**: Useful for flexibility and avoiding port conflicts, but the feature is usable end-to-end with sensible defaults even without this control, so it is lower priority than getting a working chat session with configurable credentials.

**Independent Test**: Launch the command with an explicit port flag and confirm the server binds to that port instead of the default; launch a second instance on the same default port and confirm a clear error rather than a silent failure.

**Acceptance Scenarios**:

1. **Given** the default port is already occupied by another process, **When** the user runs the launch command without specifying a port, **Then** the command fails with a clear error identifying the port conflict.
2. **Given** the user passes an explicit host/port, **When** the command runs, **Then** the printed URL reflects that host/port and the server is reachable there.

---

### Edge Cases

- What happens when the configured model/endpoint is unreachable or rejects a question *after* the server has already started (as opposed to at startup)? The chat interface must show a clear, in-conversation error for that question rather than crashing the server or leaving the request hanging.
- What happens when the user submits an empty question? The interface should not send a request to the agent for empty input.
- What happens when the agent cannot determine which dataset a question belongs to? The chat interface must show the same "could not determine an answer" style response the agent already produces for other entry points, not a raw error.
- What happens when two browser tabs/sessions are open at once? Each must see only its own conversation history, not a mixed or shared one.
- What happens when the API key is invalid rather than missing? The failure must surface as a clear per-question error in the chat, not a crash, and should not print the key value in any error output or log.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a command-line entry point that starts a local web-based chat interface for asking the agent questions, requiring no code changes to use.
- **FR-002**: The command MUST accept a way to configure the model name, the API base URL, and the API key, each individually optional on the command line when a corresponding environment variable is already set.
- **FR-003**: When a setting is provided both as a command-line flag and as an environment variable, the command-line flag MUST take precedence.
- **FR-004**: The command MUST require a model to be resolvable (from a flag or environment variable) before starting the server, and MUST fail with a clear, human-readable error — not start a partially-configured server — when no model is resolvable.
- **FR-005**: The command MUST accept configuration for the network host and port the web UI listens on, with usable defaults when not specified.
- **FR-006**: The command MUST print, on successful startup, the URL at which the web UI is reachable.
- **FR-007**: The web UI MUST let a user submit a natural-language question and display the agent's resulting answer in a conversational, chat-style layout.
- **FR-008**: The web UI MUST preserve the message history of an ongoing conversation within a session so follow-up questions are shown alongside prior questions and answers.
- **FR-009**: Answers produced through the web UI MUST come from the same question-answering behavior (dataset selection, retrieval, outcome classification) used by the project's other entry points, so results are consistent regardless of how the agent is invoked.
- **FR-010**: If a question cannot be answered (unreachable model, no matching dataset, internal failure), the web UI MUST display a clear, user-facing message for that question instead of crashing the server or leaving the request unresolved.
- **FR-011**: The system MUST NOT display or log the configured API key in the terminal output, the web UI, or any run log it writes.
- **FR-012**: Each browser session/conversation MUST be isolated from other concurrent sessions — questions and answers from one session must not appear in another.

### Key Entities

- **Launch Configuration**: The set of values needed to start the web UI for one run — model name, API base URL, API key, host, and port. Each has an optional command-line source and an optional environment-variable source, with the command-line source taking precedence.
- **Chat Session**: A single browser-side conversation with the agent, holding the ordered sequence of questions asked and answers received for the lifetime of that session.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user who already has the project installed can go from a single terminal command to a working chat interface in their browser in under 30 seconds on a local machine.
- **SC-002**: A user can switch the agent to a different model, endpoint, or credential entirely through command-line flags or environment variables, without ever opening a source file.
- **SC-003**: Running the launch command with no model configured produces a clear error message, not a crash or hang, on the first attempt.
- **SC-004**: Every answer a user receives through the web UI matches, for the same question and configuration, what they would receive by asking the same question through the project's existing testset runner.

## Assumptions

- The web UI is a developer/operator-facing tool for interactively exercising the agent, not a public multi-tenant product; it defaults to binding on a local-only interface and requires the user to deliberately opt in (via the host setting) to broader network exposure.
- No user authentication/login is required to use the web UI in this feature; access control is the operator's responsibility if they choose to expose it beyond localhost.
- Conversation history is kept only in memory for the life of the running session/process; persisting chat transcripts across restarts is out of scope for this feature (the project's existing run-log mechanism continues to capture question/answer/outcome records as it already does for other entry points).
- The web UI supports one question-answering agent configuration per running process; switching models/endpoints requires restarting the command with different configuration, not a runtime control in the UI.
- Dataset selection continues to happen automatically per question, exactly as it does today for other entry points — the web UI does not add a manual dataset picker.
