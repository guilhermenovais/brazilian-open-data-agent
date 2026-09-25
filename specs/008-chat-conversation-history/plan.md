# Implementation Plan: Conversational Context in the Web UI Chat

**Branch**: `008-chat-conversation-history` | **Date**: 2026-09-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-chat-conversation-history/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

The web UI already sends the whole visible conversation with every request, but
`web_ui.chat_api` keeps only the latest user message. This feature adds a second,
conversational path next to the unchanged single-question path:

1. **`qa_agent.answer_turn`**, a new public entry point beside `answer_question`. It takes
   the current message plus the earlier visible turns (user text and the agent's final reply
   text only, FR-001). It trims them to a configurable character budget, keeping whole turns
   and dropping the oldest first (FR-011). It then passes them to `agent.run_sync` as
   pydantic-ai `message_history` with a **new versioned prompt, `system_v2.md`**, which adds
   rules for follow-ups, clarifications, no carry-over and re-retrieving facts (FR-002 to
   FR-006). Each turn still gets a fresh `StepBudget` (FR-009) and a fresh dataset selection.
   `answer_question` and `system_v1.md` are untouched, so the testset runner's results do not
   change (FR-014, SC-007).
2. **`web_ui.chat_api`** turns the request's UI messages into `ConversationTurn`s. It reads
   the chat `id` and turn position and calls the new `ConversationalAnswerer.answer_turn`
   seam. The history is rebuilt from the browser's current view on every request, so chat
   isolation, edits and regenerations come for free with no server-side state (FR-007,
   FR-008, FR-010).
3. **Usage log**: `AgentRunLogEntry` gains an optional `conversation` block with the
   conversation id, turn index, turns used and dropped, char limit and prompt version (FR-013).
4. **Conversation evaluation**: a scripted conversation test set
   (`data/testsets/conversations/…json`) and a new `testset_runner run-conversations`
   subcommand. It replays each conversation turn by turn through `answer_turn`, reuses the
   existing retry policy and numeric matcher, adds a deterministic `expected_outcome` check
   and a figure-grounding check (SC-003), and saves one `ConversationRun` file per run (FR-015).
   The standalone `run` subcommand is unchanged.

## Technical Context

**Language/Version**: Python 3.11+ (venv currently 3.12)

**Primary Dependencies**: `pydantic-ai` 2.45.0, specifically `Agent.run_sync(message_history=…)`,
`ModelRequest`/`UserPromptPart`/`ModelResponse`/`TextPart`, and the `VercelAIAdapter`
request types (`SubmitMessage`/`RegenerateMessage` both carry `id` and `messages`). Also
`pydantic` v2 and `pydantic-settings`, both already present. No new dependency.

**Storage**: No server-side conversation storage (spec Assumptions). New artifacts:
`data/testsets/conversations/orcamentos-aeb-csv-conversations.json` (versioned test set) and
`data/conversation_runs/<run_id>.json` (one file per conversation-runner run). Entries in
`data/logs/qa_agent_runs.jsonl` gain an optional `conversation` object.

**Testing**: pytest + pyright (existing CI). `FunctionModel`-scripted contract tests check
what the model actually receives (history messages, prompt version) and that each turn gets a
fresh budget. Unit tests cover `fit_history`, UI-message→turn parsing, the conversation loader
and the grounding check. A regression test asserts the standalone path's model input is
byte-identical to before (SC-007).

**Target Platform**: Linux, local processes (`python -m web_ui.cli`, `python -m testset_runner.cli`).

**Project Type**: Single-project Python library + CLIs (`src/` layout).

**Performance Goals**: A turn's latency stays roughly that of a standalone question. History
is bounded by `history_char_limit` (default 16,000 chars, research.md R3), so input tokens
per turn are bounded too.

**Constraints**: Only visible text crosses turns, never tool calls or results (FR-001). The
standalone path is unchanged (FR-014). No credential in any run file or log (inherited 006
rules). `testset_runner` still never imports `pydantic_ai`. `qa_agent`'s history trimming is
plain Python with no framework import (Eng. 1).

**Scale/Scope**: New modules `qa_agent/conversation.py` (turn models + `fit_history`),
`qa_agent/prompts/system_v2.md`, `testset_runner/conversation_{models,loader,runner}.py`,
`testset_runner/grounding.py`. Edits to `qa_agent/{capabilities,answerer,models,settings,
prompt_loader}.py`, `web_ui/{chat_api,app,cli}.py`, `testset_runner/{cli,runner,matcher}.py`
(small refactors, no behavior change for `run`). One new test-set file with about 12
conversations.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| I. Reproducibility | SC-001 to SC-006 are measured by a re-runnable `run-conversations` pipeline over a versioned, content-hashed test set. Each run file records target, retry policy, `history_char_limit` and prompt version (FR-011, FR-015). No hand-graded one-off report is used. **Pass.** |
| II. Evidence Before Implementation | Motivated by a reproduced failure described in the spec Context: "e em 2016?" after an AEB 2015 question is declined as too vague, because `chat_api._latest_user_question` drops history. The new prompt rules are measured by the conversation runner before any claim is made. **Pass.** |
| III. Documentation Is a Deliverable | research.md, data-model.md, contracts/ and quickstart.md are produced here. Docstrings for `answer_turn`, `fit_history` and the `system_v2` rationale are carried into tasks, and the 005 chat-api contract note "earlier messages … ignored" is superseded explicitly (contracts/chat-api.md). **Pass**, carried into tasks. |
| IV. Tests Document Behavior | Contract tests map to US1–US3 acceptance scenarios at the mechanism level: what the model receives, isolation, trimming and per-turn budget. Model-quality outcomes (SC-001/002/004/005) are measured by the conversation runner, not faked with scripted doubles. **Pass.** |
| V. Separate Mechanism from Domain Knowledge | The conversation mechanics (turns, trimming, message history) contain no dataset fact. AEB-specific wording lives only in the test-set data file. `system_v2.md` is generic, like `v1`. **Pass.** |
| VI. Deterministic Over Model Judgment | Trimming, UI parsing, outcome checks and the figure-grounding check are deterministic code. Only *interpreting* a follow-up is left to the model, which is a genuine NL judgment call. Dataset selection stays deterministic on every turn (spec Assumptions). **Pass.** |
| VII. Code Quality / Simplicity | One new knob (`history_char_limit`, required by FR-011). No server-side session store, no summarisation, no tokenizer dependency (research.md R1/R3). The conversation runner reuses the matcher, the retry loop and the store pattern instead of copying them. No comparator for conversation runs (not required). **Pass.** |
| VIII. Security & Data Stewardship | History comes from the local operator's browser and is trusted like the current question (spec Assumptions). Nothing new is persisted that could hold a credential. Run files store `TargetConfiguration` (no key), as before. **Pass.** |
| IX. CI Gate | New unit and contract tests run in the existing `pytest tests/contract tests/unit` + `pyright src/` CI. The live-model runner is outside CI, like the `004` runner. **Pass.** |
| X. Usage as Research Data | Every web-UI turn is logged with conversation id, turn index and trimming stats (FR-013), so follow-up and clarification exchanges can be reconstructed from the run log. **Pass.** |
| Eng. 1 (thin wiring) | `fit_history` and turn models live in `qa_agent/conversation.py` with no `pydantic_ai` import. Converting to `ModelMessage`s is a few lines in `capabilities.py`, the existing wiring point. **Pass.** |
| Eng. 2 (interface before 2nd impl) | `ConversationalAnswerer` Protocol is added next to `QuestionAnswerer`, because `web_ui` and the conversation runner are two consumers and tests need a double. **Pass.** |
| Eng. 3 (polymorphic dispatch) | N/A. |
| Eng. 4 (DI over globals) | History, conversation context and `history_char_limit` are explicit parameters and settings. There is no module-level session store. **Pass.** |
| Eng. 5 (validated boundary) | `ConversationTurn`, `ConversationContext`, `ConversationLogContext`, `ScriptedConversation`, `ConversationRun` are pydantic models with constraints. **Pass.** |
| Eng. 6 (testable without a model) | `fit_history`, UI parsing, loader, grounding and the runner (with a fake `ConversationalAnswerer`) are all testable without a model. **Pass.** |
| Eng. 7 (typed centralized settings) | `AgentSettings.history_char_limit` (`QA_AGENT_HISTORY_CHAR_LIMIT`), with CLI flags following the existing flag-over-env convention. **Pass.** |
| Eng. 8 (versioned prompts) | The new rules go into a **new** `system_v2.md`. `system_v1.md` is not edited. The version used is recorded per log entry and run (research.md R4). **Pass.** |
| Eng. 9 (native instrumentation) | Logfire/OTel instrumentation is unchanged. With `message_history`, the history turns appear in traces natively. **Pass.** |
| Eng. 10 (static typing) | Full hints, with pyright in CI. **Pass.** |

**Post-design re-check (after Phase 1)**: still **Pass** on all rows. Phase 1 added one
Protocol (justified above), one settings field and one persisted run type, with no
dependency and no server-side state. `testset_runner` imports only `qa_agent` models and
seams, in the same direction as today.

## Project Structure

### Documentation (this feature)

```text
specs/008-chat-conversation-history/
├── plan.md                              # This file
├── research.md                          # Phase 0
├── data-model.md                        # Phase 1
├── quickstart.md                        # Phase 1
├── contracts/
│   ├── conversational-answering.md      # qa_agent.answer_turn, fit_history, ConversationalAnswerer
│   ├── chat-api.md                      # delta to 005's POST /api/chat (history now used)
│   ├── conversation-testset.md          # scripted conversation file format + scoring rules
│   └── cli.md                           # --history-char-limit, `run-conversations` subcommand
├── checklists/requirements.md           # from /speckit-specify
└── tasks.md                             # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
src/
├── qa_agent/
│   ├── conversation.py        # NEW: ConversationTurn, ConversationContext, fit_history (no pydantic_ai)
│   ├── capabilities.py        # + answer_turn; _answer_with_selection gains history/prompt_version/log ctx
│   ├── answerer.py            # + ConversationalAnswerer Protocol; QaAgentQuestionAnswerer.answer_turn
│   ├── models.py              # + ConversationLogContext; AgentRunLogEntry.conversation (optional)
│   ├── settings.py            # + history_char_limit
│   ├── prompt_loader.py       # render(briefing, version="v1") — v1 default keeps callers unchanged
│   └── prompts/system_v2.md   # NEW: v1 rules + conversation rules
├── web_ui/
│   ├── chat_api.py            # _latest_user_question → _conversation_from(adapter); calls answer_turn
│   ├── app.py                 # typed against ConversationalAnswerer
│   └── cli.py                 # + --history-char-limit
└── testset_runner/
    ├── conversation_models.py # NEW: ScriptedTurn, ScriptedConversation, ConversationTestset, TurnResult, ConversationRun…
    ├── conversation_loader.py # NEW: load + validate + hash the conversation test set
    ├── conversation_runner.py # NEW: run_conversations (replay, retry, score, summarize, save)
    ├── grounding.py           # NEW: ungrounded_figures(answer, message, steps)
    ├── runner.py              # _ask_with_retry generalized to take a callable (no behavior change)
    ├── matcher.py             # numeric-substring regex made public for grounding.py
    ├── store.py               # + JsonFileConversationRunStore
    └── cli.py                 # + run-conversations subcommand

data/testsets/conversations/orcamentos-aeb-csv-conversations.json   # NEW

tests/
├── unit/qa_agent/test_conversation.py            # fit_history, turn models
├── unit/qa_agent/test_prompt_loader.py           # + v2 renders, v1 unchanged
├── unit/web_ui/test_chat_api_history.py          # UI messages → turns / context
├── unit/testset_runner/test_conversation_loader.py
├── unit/testset_runner/test_grounding.py
├── contract/qa_agent/test_answer_turn.py         # history reaches model, v2 prompt, per-turn budget, logging
├── contract/qa_agent/test_standalone_unchanged.py# SC-007: answer_question model input identical
├── contract/web_ui/test_chat_endpoint.py         # + history forwarded, isolation by payload
└── contract/testset_runner/test_run_conversations.py
```

**Structure Decision**: Keep the existing single `src/` layout. The conversational core goes
in `qa_agent`, the one package that owns answering. `web_ui` stays a thin adapter. The
conversation runner is a second mode of `testset_runner`, placed in its own `conversation_*`
modules so the standalone `run` code path is not branched (FR-014/FR-015).

## Complexity Tracking

No Constitution Check violations. The table is intentionally empty.
