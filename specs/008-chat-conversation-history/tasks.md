---

description: "Task list for 008 — Conversational Context in the Web UI Chat"
---

# Tasks: Conversational Context in the Web UI Chat

**Input**: Design documents from `/specs/008-chat-conversation-history/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (conversational-answering.md, chat-api.md, conversation-testset.md, cli.md), quickstart.md

**Tests**: INCLUDED. The plan's Testing section and quickstart.md §1 name specific unit and contract test files, and Constitution Principles IV/IX make tests part of done. Model-quality outcomes (SC-001/002/004/005/006) are measured by the live `run-conversations` runner, not by scripted doubles.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: The user story the task belongs to (US1, US2, US3)
- Paths are relative to the repository root (single `src/` layout, per plan.md)

## Invariants every task must respect

- `answer_question`, `system_v1.md` and `testset_runner run` / `compare` behavior stay unchanged (FR-014, SC-007). `system_v1.md` MUST NOT be edited (Eng. 8).
- Only visible text crosses turns: build `UserPromptPart` / `TextPart` only, never `ToolCallPart` / `ToolReturnPart` from earlier turns (FR-001).
- `qa_agent/conversation.py` MUST NOT import `pydantic_ai` (Eng. 1). `testset_runner` MUST NOT import `pydantic_ai`.
- No server-side conversation state and no module-level session store (research.md R1, Eng. 4).
- Run `pytest tests/contract tests/unit` and `pyright src/` after each phase.

## Live validation target

All live checks (T037, T042, T047, T052) run against the local vLLM server:

```bash
--model Qwen/Qwen3-8B-AWQ --base-url http://localhost:8000/v1 --api-key EMPTY
```

(or export `QA_AGENT_MODEL=Qwen/Qwen3-8B-AWQ`, `QA_AGENT_BASE_URL=http://localhost:8000/v1`, `QA_AGENT_API_KEY=EMPTY`). Check it is up with `curl -s http://localhost:8000/v1/models`. vLLM occupies port 8000, which is also the web UI's default, so the manual web UI check MUST pass `--port 8001` and use `http://127.0.0.1:8001`. The server's `max_model_len` is 40,960 tokens, so the default 16,000-character history limit fits well. Record the model id and base URL in `results.md` (T053).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Directory and ignore-file scaffolding for the new artifacts.

- [X] T001 [P] Add `data/conversation_runs/` to `.gitignore` (next to the existing `data/testset_runs/` line) so conversation-runner output is not committed, matching how `testset_runner run` output is treated
- [X] T002 [P] Create the directory `data/testsets/conversations/` (the test-set file itself is filled per story in T036, T041, T046)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The conversational core in `qa_agent` (models, trimming, log block, settings, prompt versioning, shared-core refactor) and the conversation evaluation harness in `testset_runner`. Every user story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### 2a. qa_agent conversational core

- [X] T003 [P] Create `src/qa_agent/conversation.py` (NO `pydantic_ai` import) with pydantic v2 models per data-model.md: `ConversationTurn` with `question: str` (`min_length=1`, "The user's message text, stripped") and `answer: str | None` ("`None` when the turn has no reply … Never contains tool calls or results"), plus a derived `size` property `= len(question) + len(answer or "")`; and `ConversationContext` with `conversation_id: str` (`min_length=1`), `turn_index: int` (`≥ 1`; "equals `len(history) + 1` before trimming, because trimming never renumbers") and `history: list[ConversationTurn]` ("Oldest first. Full, untrimmed."). Include a module docstring explaining that only visible text is modelled (FR-001)
- [X] T004 In `src/qa_agent/conversation.py` implement `fit_history(turns: list[ConversationTurn], char_limit: int) -> list[ConversationTurn]` per contracts/conversational-answering.md: walk from the newest turn backwards summing `size`; stop at the **first** turn that does not fit; return the kept contiguous suffix in original order; `char_limit == 0` or `turns == []` returns `[]`; never truncates text; pure and never raises for valid input. Docstring must explain the "stop at first non-fitting turn, never skip-and-pack" rationale (research.md R3) (depends on T003)
- [X] T005 [P] Write `tests/unit/qa_agent/test_conversation.py`: `ConversationTurn` rejects empty `question`, `size` counts `answer=None` as 0, `ConversationContext` rejects `turn_index=0` and empty `conversation_id`; `fit_history` cases — empty input, `char_limit=0`, everything fits, result is a suffix in order, result is maximal (adding the previous turn would exceed the limit), a large middle turn stops the walk even when older small turns would fit, a single newest turn larger than the limit returns `[]`, text is never truncated (depends on T004)
- [X] T006 [P] In `src/qa_agent/models.py` add `ConversationLogContext` (pydantic model) with `conversation_id: str`, `turn_index: int` (`≥ 1`), `history_turns_used: int` (`≥ 0`), `history_turns_dropped: int` (`≥ 0`), `history_char_limit: int` (`≥ 0`), `prompt_version: str`; extend `AgentRunLogEntry` with `conversation: ConversationLogContext | None = None` and update its docstring to say it is one per `answer_question` **or** `answer_turn` call and `question` is the current message as typed (data-model.md)
- [X] T007 [P] Extend `tests/unit/qa_agent/test_run_log.py`: an `AgentRunLogEntry` with a `conversation` block round-trips through `JsonlRunLogger` JSONL; a pre-existing log line without a `conversation` key still validates with `conversation is None` (backward compatibility) (depends on T006)
- [X] T008 [P] In `src/qa_agent/settings.py` add `history_char_limit: int = Field(16_000, ge=0)` to `AgentSettings` (env `QA_AGENT_HISTORY_CHAR_LIMIT` via the existing `QA_AGENT_` prefix), with a comment that the standalone path ignores it and why 16,000 (research.md R3: ≥ 20 typical turns, SC-006)
- [X] T009 [P] In `src/qa_agent/prompt_loader.py` change to `render(briefing: str, version: str = "v1") -> str`, loading `prompts/system_{version}.md`; an unknown version raises `FileNotFoundError` (programming error). Existing callers keep the `"v1"` default unchanged
- [X] T010 [P] Extend `tests/unit/qa_agent/test_prompt_loader.py`: `render(briefing)` output is byte-identical to `render(briefing, version="v1")`; `render(briefing, version="nope")` raises `FileNotFoundError` (v2 assertions are added in T030/T039) (depends on T009)
- [X] T011 Refactor `_answer_with_selection` in `src/qa_agent/capabilities.py`: add keyword-only `history: Sequence[ConversationTurn] = ()`, `prompt_version: str = "v1"` and `log_context: ConversationLogContext | None = None`. Build `message_history` from `history` as `ModelRequest(parts=[UserPromptPart(question)])` followed by `ModelResponse(parts=[TextPart(answer)])` only when `answer is not None` (no other part types, FR-001); pass `message_history=... or None` to `agent.run_sync` so the standalone call is unchanged; call `render(selection.briefing, version=prompt_version)`; switch step extraction to `run_result.new_messages()` (research.md R2); thread `log_context` into `_finalize` so the `AgentRunLogEntry` gets `conversation=log_context` on success and on failure. Defaults MUST reproduce today's call exactly (depends on T003, T006, T009)
- [X] T012 Write `tests/contract/qa_agent/test_standalone_unchanged.py` (SC-007, FR-014) using a `FunctionModel` that captures its `messages` and `AgentInfo.instructions`: drive `_answer_with_selection` with default kwargs and assert the model receives exactly one `ModelRequest` whose only user part is the question (no earlier history), instructions equal `render(briefing)` rendered from `system_v1.md`, and the JSONL log line has `"conversation": null`. Follow the fixture style of `tests/contract/qa_agent/test_answer_question_dispatch.py` (real briefing/dataset under `data/`) (depends on T011)
- [X] T013 Add `ConversationalAnswerer` Protocol to `src/qa_agent/answerer.py` next to `QuestionAnswerer`: `def answer_turn(self, message: str, context: ConversationContext) -> QuestionAnsweringResult: ...`, with a docstring citing the two consumers (web UI, conversation runner) per Eng. 2. Also export module constant `CONVERSATION_PROMPT_VERSION = "v2"` from `src/qa_agent/capabilities.py` (the single source of truth used by `answer_turn` and recorded by the runner) (depends on T003)

### 2b. Conversation evaluation harness (testset_runner, FR-015)

- [X] T014 [P] Refactor `_ask_with_retry` in `src/testset_runner/runner.py` to take `ask: Callable[[], QuestionAnsweringResult]` instead of an answerer + question; update the single call in `run_testset` to pass `lambda: answerer.answer(question.question)`. Pure mechanical change — no behavior change; existing `tests/contract/testset_runner/test_retry.py` and `test_run_testset.py` must pass unmodified (update only call sites in tests if they call `_ask_with_retry` directly)
- [X] T015 [P] In `src/testset_runner/matcher.py` rename `_NUMERIC_SUBSTRING` to public `NUMERIC_SUBSTRING` (update internal uses) so `grounding.py` can reuse the exact regex; no behavior change
- [X] T016 [P] Create `src/testset_runner/conversation_models.py` with pydantic models per data-model.md: `ScriptedTurn` (`message: str` `min_length=1`; `expected: str | None` "Same grammar as `Question.expected`"; `expected_outcome: Literal["full","partial","none"] | None`; `source: str | None`; `scored: bool | None` — "`None` means scored iff `expected` or `expected_outcome` is set. `false` forces a context-only turn. `true` without either expectation is a load error", exposed via an `is_scored` property); `ScriptedConversation` (`id` `min_length=1`, `category` `min_length=1`, `description: str = ""`, `turns` `min_length=1`); `ConversationTestset` (`path`, `content_hash`, `conversations`); `TurnResult` (all fields in data-model.md incl. `history_turns_sent`, `history_turns_used` (`ge=0`), `status: Literal["matched","not_matched","needs_review","errored","unscored"]`, `ungrounded_figures: list[str]`, `attempts` `≥ 1`, `failed_attempts: list[FailureDetail]`, `failure: FailureDetail | None`); `ConversationResult`; `ConversationRunSummary` (with nested `by_category: dict[str, ConversationRunSummary]` and `turns_with_ungrounded_figures`, `target_unreachable`); `ConversationRun` (`run_id`, `created_at`, `testset`, `target: TargetConfiguration`, `retry_policy: RetryPolicy`, `history_char_limit: int`, `prompt_version: str`, `results`, `summary`). Reuse `RetrievalStep`/`FailureDetail` from `qa_agent.models` and `TargetConfiguration`/`RetryPolicy` from `testset_runner.models`
- [X] T017 Create `src/testset_runner/conversation_loader.py` with `ConversationTestsetLoader.load(path) -> ConversationTestset`: sha256 of raw bytes as `content_hash`; raise the existing `TestsetLoadError` when the file is unreadable/not JSON, any record fails validation, `id`s are duplicated, or a turn has `scored: true` with neither `expected` nor `expected_outcome` (contracts/conversation-testset.md "Loader rules"). Mirror `src/testset_runner/loader.py` style (depends on T016)
- [X] T018 [P] Write `tests/unit/testset_runner/test_conversation_loader.py`: valid file loads with correct hash; each loader-rule violation raises `TestsetLoadError`; `scored` defaults (`None` + `expected` → scored, `None` + nothing → unscored, `false` + `expected` → unscored) (depends on T017)
- [X] T019 [P] Create `src/testset_runner/grounding.py` with `ungrounded_figures(answer: str, message: str, steps: list[RetrievalStep]) -> list[str]`: numeric substrings of `answer` found by `matcher.NUMERIC_SUBSTRING`, parsed with `parse_locale_number` (unparseable ignored), whose value equals no value parsed from `message` or any `step.result_summary`; keep first-appearance order, drop duplicates. Docstring: reported not scored, computed values (e.g. differences) are a known false positive (research.md R11, SC-003) (depends on T015)
- [X] T020 [P] Write `tests/unit/testset_runner/test_grounding.py`: figure present in a step summary is grounded (including different locale formatting of the same value); year taken from the user message is grounded; a figure only present in an earlier answer (not in current steps) is flagged; duplicates reported once in order; answer with no numbers returns `[]` (depends on T019)
- [X] T021 [P] Add `JsonFileConversationRunStore(out_dir)` and a `ConversationRunStore` Protocol to `src/testset_runner/store.py`: `save(run) -> str` writes `<out_dir>/<run_id>.json` with indent 2 (creating the dir); `load(path) -> ConversationRun` raises `RunLoadError` on read or validation failure. Mirror `JsonFileRunStore`; extend `tests/unit/testset_runner/test_store.py` with a round-trip and a bad-file case (depends on T016)
- [X] T022 Create `src/testset_runner/conversation_runner.py` with `run_conversations(testset_path, target, *, answerer: ConversationalAnswerer, store: ConversationRunStore, history_char_limit: int, prompt_version: str = CONVERSATION_PROMPT_VERSION, matcher: MatchStrategy = NumericMatchStrategy(), retry_policy: RetryPolicy = RetryPolicy(), sleep=time.sleep) -> ConversationRun` exactly per contracts/conversation-testset.md: load (errors propagate, nothing saved); generate `run_id` (`%Y%m%dT%H%M%S%fZ`) up front; per conversation start `history = []`; per turn k build `ConversationContext(conversation_id=f"{run_id}:{conv.id}", turn_index=k, history=list(history))`, call `_ask_with_retry(lambda: answerer.answer_turn(turn.message, context), retry_policy, sleep)`, record `history_turns_sent=len(context.history)` and `history_turns_used=len(fit_history(context.history, history_char_limit))` (pure `qa_agent.conversation` import, no `pydantic_ai`), append `ConversationTurn(question=turn.message, answer=result.answer)` even when errored; score per the "Turn scoring" block (`errored` → `unscored` → worst of numeric grade and exact `expected_outcome` check, order `not_matched < needs_review < matched`); compute `ungrounded_figures` for every non-errored turn; summarize (`match_rate = matched / scored_turns` or 0.0, `by_status`, one-level `by_category`, `turns_with_ungrounded_figures`, `target_unreachable` = at least one turn with `dataset_key != "<none>"` and all such turns errored); save and return. Imports only `qa_agent` models/seams, never `pydantic_ai` (depends on T004, T013, T014, T017, T019, T021)
- [X] T023 Write `tests/contract/testset_runner/test_run_conversations.py` with a fake `ConversationalAnswerer` that records every `(message, context)` it receives: history grows turn by turn with the fake's **actual** answers; each conversation starts with empty history and a distinct `conversation_id` `"<run_id>:<conv.id>"`; `turn_index` is 1-based; `history_turns_sent`/`history_turns_used` are equal when the history fits and `history_turns_used < history_turns_sent` with a small `history_char_limit`; an errored turn's failure text is still appended to history and later turns still run; scoring table cases (numeric match, outcome mismatch → `not_matched`, numeric `needs_review` + outcome matched → `needs_review`, unscored); `ungrounded_figures` populated; summary counts and `by_category`; `target_unreachable`; saved run file round-trips through `JsonFileConversationRunStore.load`; a `TestsetLoadError` saves nothing (depends on T022)

**Checkpoint**: `pytest tests/contract tests/unit` and `pyright src/` pass; the standalone path is proven unchanged (T012); the runner (`run_conversations`) works against a fake answerer. The `run-conversations` CLI subcommand (T024/T025) comes in US1, once `QaAgentQuestionAnswerer.answer_turn` exists.

---

## Phase 3: User Story 1 - Ask a follow-up question that depends on earlier turns (Priority: P1) 🎯 MVP

**Goal**: In a web UI chat, a follow-up such as "e em 2016?" is answered using the earlier visible turns, with every fact retrieved again in the current turn.

**Independent Test**: In a new chat, ask "Quanto foi pago pela AEB em 2015?" then "e em 2016?". The second answer gives the 2016 paid amount matching the data, without restating context (quickstart.md §2 step 1). Offline: `tests/contract/qa_agent/test_answer_turn.py` and `tests/contract/web_ui/test_chat_endpoint.py` pass.

### Tests for User Story 1

- [X] T026 [P] [US1] Write `tests/contract/qa_agent/test_answer_turn.py` (FunctionModel-scripted, fixtures like `test_answer_question_dispatch.py`): (a) the model receives each kept history turn as a `ModelRequest` with a `UserPromptPart(question)` followed by a `ModelResponse` with a `TextPart(answer)`, a turn with `answer=None` yields only the request, and **no** `ToolCallPart`/`ToolReturnPart` from earlier turns appears (FR-001); (b) instructions are rendered from `system_v2.md`; (c) a turn after a turn that used all 10 retrieval steps still gets a fresh `StepBudget` of 10 (FR-009, capture via `capture_deps`); (d) `QuestionAnsweringResult.steps` holds only current-turn retrievals; (e) exactly one JSONL log line with `conversation` = `{conversation_id, turn_index, history_turns_used, history_turns_dropped, history_char_limit, prompt_version: "v2"}`; (f) with a small `history_char_limit`, the oldest turns are dropped, `history_turns_dropped > 0`, and the turn is still answered (FR-011); (g) `answer_turn` delegates to `_answer_with_selection` after a real selection (monkeypatch, as in C1 of the dispatch test) and a selection failure returns `_NO_DATASET_ANSWER` with `errored=True` and a log entry that still carries the `conversation` block
- [X] T027 [P] [US1] Write `tests/unit/web_ui/test_chat_api_history.py` for `_conversation_from` (contracts/chat-api.md step 2): current message is the stripped text of the **last** non-empty user message and anything after it is ignored; earlier user messages open turns; following assistant `TextUIPart` texts are joined with `"\n\n"`, stripped, into that turn's `answer`; a user message with no reply gives `answer=None`; tool/reasoning/file/source parts, `system` messages and assistant text before the first user message are dropped; `conversation_id == run_input.id`; `turn_index == len(history) + 1`; a payload with no non-empty user message returns `None`; both `SubmitMessage` and `RegenerateMessage` inputs work
- [X] T028 [P] [US1] Extend `tests/contract/web_ui/test_chat_endpoint.py`: replace/extend the answerer double so it implements `answer_turn` and records calls; the contract example payload (`chat-1`, three messages) produces `answer_turn("e em 2016?", ConversationContext(conversation_id="chat-1", turn_index=2, history=[ConversationTurn(question="Quanto foi pago pela AEB em 2015?", answer="Em 2015, o valor pago foi de R$ …")]))`; the empty-input short-circuit and generic `ErrorChunk` on exception still behave as in 005

### Implementation for User Story 1

- [X] T029 [US1] Create `src/qa_agent/prompts/system_v2.md`: copy all eight v1 rules unchanged (FR-012) except rule 2 reworded from "neste mesmo atendimento" to "nesta mesma resposta, durante o turno atual"; add a "Conversa" section (Portuguese, generic, no dataset facts — Principle V) stating that earlier messages serve only to interpret the current message (FR-002/FR-005); a message that is complete on its own does not inherit subject, period, filter or metric (FR-004); for an ambiguous reference pick the most reasonable reading and state it (FR-006); values from earlier replies must be queried again, never repeated (FR-005); earlier failure or decline messages are not facts (Edge Cases); a follow-up about something the data does not cover is declined, not answered from the earlier subject. Leave a clearly marked place for the clarification rule added in T040. Keep the `{briefing}` placeholder exactly as v1 uses it. Do NOT modify `system_v1.md`
- [X] T030 [P] [US1] Extend `tests/unit/qa_agent/test_prompt_loader.py`: `render(briefing, version="v2")` succeeds, contains the briefing, contains every v1 rule except the reworded rule 2 (assert rule texts by comparing against `system_v1.md` lines), and contains a "Conversa" section; `system_v1.md` content is unchanged (hash or snapshot compare against git HEAD content read in the test) (depends on T029)
- [X] T031 [US1] Implement `answer_turn(message, *, context: ConversationContext, selector, selection_logger, run_logger, settings) -> QuestionAnsweringResult` in `src/qa_agent/capabilities.py` per contracts/conversational-answering.md: `select_dataset(message, …)` every turn (selection failure → `_NO_DATASET_ANSWER`, `outcome="none"`, `errored=True`, same `describe_failure` as `answer_question`, log entry **with** the conversation block); `kept = fit_history(context.history, settings.history_char_limit)`; build `ConversationLogContext(conversation_id, turn_index, history_turns_used=len(kept), history_turns_dropped=len(context.history)-len(kept), history_char_limit=settings.history_char_limit, prompt_version=CONVERSATION_PROMPT_VERSION)`; call `_answer_with_selection(message, selection, run_logger=…, settings=…, history=kept, prompt_version=CONVERSATION_PROMPT_VERSION, log_context=…)`. Same catch policy as `answer_question`. Docstring explaining why it is a separate entry point (FR-014) and that trimming happens here, not in callers (depends on T004, T011, T013, T029)
- [X] T032 [US1] In `src/qa_agent/answerer.py` extend `QaAgentQuestionAnswerer`: constructor keyword `history_char_limit: int = 16_000` forwarded into its `AgentSettings`, exposed read-only as property `history_char_limit`; add `answer_turn(self, message, context)` delegating to `capabilities.answer_turn` with the same selector/loggers/settings as `answer`. `answer` is unchanged. The class now satisfies both `QuestionAnswerer` and `ConversationalAnswerer` (depends on T031)
- [X] T033 [US1] In `src/web_ui/chat_api.py` replace `_latest_user_question(adapter)` with `_conversation_from(run_input) -> tuple[str, ConversationContext] | None` per contracts/chat-api.md step 2 / research.md R7 (text-only parse of `TextUIPart`s, no use of `VercelAIAdapter.messages`/`load_messages`); change `build_chat_endpoint(answerer: ConversationalAnswerer)` to call `answerer.answer_turn(message, context)` in the thread pool (step 4); `None` keeps today's empty `FinishChunk` response. Update the module docstring to say it supersedes 005 contracts/chat-api.md step 2 "earlier messages … ignored" (depends on T013)
- [X] T034 [US1] In `src/web_ui/app.py` type `create_app(answerer: ConversationalAnswerer, host: str)` against the new Protocol (depends on T033)
- [X] T035 [US1] In `src/web_ui/cli.py` add `--history-char-limit` (fallback `QA_AGENT_HISTORY_CHAR_LIMIT`, default `16000`, integer ≥ 0 else `Error: --history-char-limit must be an integer >= 0.` on stderr and exit 1), pass it to `QaAgentQuestionAnswerer(history_char_limit=…)`, and print `Conversation history limit: <n> characters` on the line after `Chat UI available at: …`; extend `tests/unit/web_ui/test_cli.py` for the flag, env fallback, validation error and startup line (depends on T032)
- [X] T024 [US1] Add the `run-conversations` subcommand to `src/testset_runner/cli.py` per contracts/cli.md: flags `--testset` (required), `--model`, `--base-url`, `--api-key`, `--max-attempts`, `--history-char-limit`, `--out-dir` (default `data/conversation_runs`), flag-over-env precedence with `QA_AGENT_*` envs; build `QaAgentQuestionAnswerer(..., history_char_limit=limit)` and pass the same `limit` to `run_conversations`; error messages on stderr / exit 1 identical to `run` plus `Error: --history-char-limit must be an integer >= 0.`; print the report format in contracts/cli.md (run line, optional unreachable WARNING, match rate, per-category lines, `Turns with ungrounded figures: N`, retry policy via existing `_describe_policy`, `History limit: <n> characters; prompt: <v>`, `Saved run to …`). `run` and `compare` stay unchanged (depends on T022, T032: it needs `QaAgentQuestionAnswerer.history_char_limit` and `answer_turn`, which is why it lives in US1 and not Phase 2)
- [X] T025 [US1] Extend `tests/unit/testset_runner/test_cli.py`: `run-conversations` parser accepts all flags; negative/non-integer `--history-char-limit` yields the exact error and exit 1; env fallback for `QA_AGENT_HISTORY_CHAR_LIMIT`; report formatting with a stubbed `run_conversations` (monkeypatched) including the category lines and history/prompt line; the existing `run` tests still pass unchanged (depends on T024)
- [X] T036 [P] [US1] Add US1 conversations to `data/testsets/conversations/orcamentos-aeb-csv-conversations.json` per contracts/conversation-testset.md: ≥ 3 `follow-up-year`, ≥ 3 `follow-up-metric`, ≥ 3 `follow-up-reference` (last turn scored, SC-001), ≥ 2 `standalone-after-unrelated` (SC-004), and 1 `long-conversation` with ≥ 20 turns (SC-006). Follow the "only the measured turn is scored" convention in contracts/conversation-testset.md: every context turn (the first question of a follow-up, the unrelated turns before a standalone question) sets `"scored": false`, so each category's match rate is exactly its criterion. Every `expected` value MUST be computed by a deterministic pandas query over `data/datasets/…/dados_gerais/tb_geral.csv` (never hand-read or model output) with `source` set; save the one-off computation script under `specs/008-chat-conversation-history/` or record the exact query in each conversation's `description` so the values are reproducible (Principles I/VI)
- [ ] T037 [US1] Live check (not CI): run `python -m testset_runner.cli run-conversations --testset data/testsets/conversations/orcamentos-aeb-csv-conversations.json`; confirm SC-001 (≥ 90% on the three follow-up categories), SC-004 (100% on `standalone-after-unrelated`), SC-006 (0 `errored` in `long-conversation`, and `history_turns_used == history_turns_sent` on every one of its turns at the default limit, FR-011) and give every flagged figure in `turns_with_ungrounded_figures` a `derived` / `ungrounded` verdict with a reason per contracts/conversation-testset.md "Resolving flagged figures" (SC-003: 0 `ungrounded`). Repeat with `--history-char-limit 500` and confirm every turn is answered and late turns show `history_turns_used < history_turns_sent` in the run file (FR-011). Record the run id(s) and verdicts for T053 (depends on T024, T032, T036) — **Executed 2026-09-25; criteria not met (SC-001 5/9, SC-003 5 ungrounded; SC-004, SC-006 and FR-011 met). See results.md.**

**Checkpoint**: Follow-ups work in the web UI and in the runner; US1 is independently shippable (MVP).

---

## Phase 4: User Story 2 - Answer the agent's request for clarification (Priority: P1)

**Goal**: When the agent's last reply asked for more detail, the user's short reply is combined with the original question and answered.

**Independent Test**: In a new chat, send "Me fale sobre o orçamento.", get a clarification request, reply "o valor pago em 2015" → the answer is the 2015 paid amount (quickstart.md §2 step 2).

### Tests for User Story 2

- [X] T038 [P] [US2] Add a case to `tests/contract/qa_agent/test_answer_turn.py`: with history `[ConversationTurn(question="Me fale sobre o orçamento.", answer=<clarification request text>)]` and message `"o valor pago em 2015"`, the model receives the original vague question and the clarification reply as prior `UserPromptPart`/`TextPart` messages and the short reply as the current user prompt (mechanism-level check for FR-003; answer quality is measured in T041)
- [X] T039 [P] [US2] Extend `tests/unit/qa_agent/test_prompt_loader.py`: the rendered v2 prompt contains the clarification rule text added in T040 (depends on T040)

### Implementation for User Story 2

- [X] T040 [US2] Add the clarification rule to the "Conversa" section of `src/qa_agent/prompts/system_v2.md` (at the place marked in T029): if the previous reply asked the user to clarify or narrow the question, read the new message as a possible answer to it and, if it is, combine it with the original question before answering (FR-003, US2-AS1); if the combined question is still underspecified, ask again for what is missing and do not guess (US2-AS2); if the new message is a different, complete question, answer it on its own (US2-AS3). Do not change *when* the agent asks for clarification (spec Assumptions). This must land before any recorded `run-conversations` run is cited as evidence for v2; if T037 already recorded a run, note in the PR that v2 changed after it and re-run T037 (Eng. 8)
- [X] T041 [P] [US2] Add US2 conversations to `data/testsets/conversations/orcamentos-aeb-csv-conversations.json`: ≥ 3 `clarification` conversations (vague first turn `scored: false`, optionally documenting `expected_outcome: "none"`; the reply turn, the only scored turn, completes the question and has a pandas-computed `expected` + `source`, SC-002); ≥ 1 `clarification-insufficient` conversation (vague first turn `scored: false`; a reply that still leaves the question underspecified, scored with `expected_outcome: "none"`, US2-AS2), kept out of `clarification` so its expected decline does not count toward SC-002; ≥ 1 `clarification-ignored` conversation (vague first turn `scored: false` → an unrelated complete question with a computed `expected`, US2-AS3)
- [ ] T042 [US2] Live check (not CI): re-run `run-conversations` and confirm SC-002 (≥ 90% on `clarification`, which scores only the reply turns), that `clarification-insufficient` (US2-AS2) and `clarification-ignored` (US2-AS3) turns are matched, and record verdicts for any new flagged figures (SC-003); confirm SC-001/SC-004 did not regress after the v2 edit; record the run id (depends on T040, T041) — **Executed 2026-09-25; criteria not met (SC-002 2/3; clarification-insufficient 0/1; clarification-ignored 1/1). See results.md.**

**Checkpoint**: US1 and US2 both work; clarification replies are answered in context.

---

## Phase 5: User Story 3 - Start a fresh conversation without leftover context (Priority: P2)

**Goal**: A new chat has no context from earlier chats; concurrent chats are isolated.

**Independent Test**: After a conversation about 2015, open a new chat and send "e em 2016?" → the agent says the question is too vague (quickstart.md §2 step 3).

### Tests for User Story 3

- [X] T043 [P] [US3] Extend `tests/contract/web_ui/test_chat_endpoint.py` (FR-007/FR-008, US3-AS1/AS2): two interleaved requests with different chat `id`s produce `ConversationContext`s containing only their own messages and their own `conversation_id`; a new chat's first request (single user message) yields `history == []` and `turn_index == 1` even after other chats' requests on the same app instance (proves no server-side state)
- [X] T044 [P] [US3] Add a case to `tests/unit/web_ui/test_chat_api_history.py` for a `RegenerateMessage` payload already sliced by the client (FR-010): the history reflects exactly the payload's current messages and no discarded version
- [X] T045 [P] [US3] Add a case to `tests/contract/testset_runner/test_run_conversations.py`: the first turn of every scripted conversation receives `history == []` regardless of what earlier conversations in the same run answered (SC-005 isolation)

### Implementation for User Story 3

- [X] T046 [P] [US3] Add ≥ 2 `fresh-chat-follow-up` conversations to `data/testsets/conversations/orcamentos-aeb-csv-conversations.json`: single-turn follow-up-style first messages (e.g. `"e em 2016?"`, `"e o empenhado?"`) with `expected_outcome: "none"` (SC-005)
- [ ] T047 [US3] Live check (not CI): re-run `run-conversations` and confirm SC-005 (100% on `fresh-chat-follow-up`); then do the manual web UI walkthrough in quickstart.md §2 steps 1–4 with `python -m web_ui.cli --port 8001` (vLLM holds 8000; see "Live validation target"), including `tail -n 3 data/logs/qa_agent_runs.jsonl` showing `conversation.conversation_id` equal to each chat's URL id with `turn_index` 1, 2, … (FR-013) (depends on T046, T035) — **Executed 2026-09-25; criteria not met (SC-005 0/2; walkthrough steps 1 and 4 pass, 2 and 3 fail). See results.md.**

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, regression proof and final validation.

- [X] T048 [P] Add a "Superseded by 008" note to `specs/005-cli-web-ui/contracts/chat-api.md` step 2 pointing to `specs/008-chat-conversation-history/contracts/chat-api.md` (Principle III; plan Constitution Check row III)
- [X] T049 [P] Add a note to `specs/003-qa-agent-workflow/spec.md` FR-011 / first Assumption (the single-question contract) stating that 008 adds a conversational path for the web UI and conversation runner while the single-question contract stays in force elsewhere
- [X] T050 [P] Review docstrings for `answer_turn`, `_answer_with_selection` (new kwargs), `fit_history`, `ConversationalAnswerer`, `_conversation_from`, `run_conversations`, `ungrounded_figures`; add a short header comment in `src/qa_agent/prompts/system_v2.md`-adjacent docs (e.g. `prompt_loader.py` docstring) recording why v2 exists and that v1 is frozen for the standalone path (research.md R4)
- [X] T051 Run `pytest tests/contract tests/unit` and `pyright src/`; fix any failure. Confirm `grep -n "pydantic_ai" src/qa_agent/conversation.py src/testset_runner/*.py` returns nothing
- [X] T052 SC-007 regression: run `python -m testset_runner.cli run --testset data/testsets/orcamentos-aeb-csv-10.json` and confirm the report format and run-file shape are unchanged; `test_standalone_unchanged.py` is the deterministic proof (quickstart.md §4)
- [X] T053 Write a short results note in `specs/008-chat-conversation-history/results.md` listing the recorded `run-conversations` run ids, per-SC outcomes (SC-001…SC-006) with the numbers from each run's `summary`, a verdict table for every flagged figure (`run_id`, conversation `id`, `turn_index`, figure, `derived`/`ungrounded`, reason — contracts/conversation-testset.md "Resolving flagged figures"), and the prompt version / history limit used (Principles I/II)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: after Setup. BLOCKS all user stories. 2a and 2b can proceed in parallel; T022 needs T004 and T013 from 2a.
- **US1 (Phase 3)**: after Phase 2. It is the MVP and adds `answer_turn`, `system_v2.md`, the web wiring and the `run-conversations` CLI (T024/T025).
- **US2 (Phase 4)**: after US1's T029 (prompt file exists) and T031/T032 (answer path exists). Its tests and data (T038, T041) can start as soon as Phase 2 is done.
- **US3 (Phase 5)**: after US1's T033 (chat endpoint uses `answer_turn`). Its tests and data (T043–T046) can start as soon as Phase 2 is done.
- **Polish (Phase 6)**: after the desired stories are complete.

### User Story Dependencies

- **US1 (P1)**: Foundational only.
- **US2 (P1)**: extends the `system_v2.md` created in US1 and uses its `answer_turn`; independently testable by its own clarification conversations and the manual step 2.
- **US3 (P2)**: relies on US1's chat wiring; isolation holds by construction and is verified by its own tests and fresh-chat conversations.

### Key task-level dependencies

- T003 → T004 → T005; T006 → T007; T009 → T010
- T003 + T006 + T009 → T011 → T012
- T015 → T019 → T020; T016 → T017 → T018; T016 → T021
- T004 + T013 + T014 + T017 + T019 + T021 → T022 → T023
- T029 → T030; T004 + T011 + T013 + T029 → T031 → T032 → T035; T022 + T032 → T024 → T025
- T013 → T033 → T034
- T024 + T032 + T036 → T037; T040 + T041 → T042; T046 + T035 → T047

### Parallel Opportunities

- Phase 1: T001, T002.
- Phase 2: T003, T006, T008, T009, T014, T015, T016 all touch different files and can start together; then T005, T007, T010, T018, T020, T021.
- US1: tests T026, T027, T028 in parallel; T036 (test-set data) in parallel with all code tasks.
- US2 and US3 test/data tasks (T038, T041, T043–T046) can run in parallel with US1 implementation once Phase 2 is done.
- Polish: T048, T049, T050 in parallel.

---

## Parallel Example: User Story 1

```bash
# Tests first, all different files:
Task: "Write tests/contract/qa_agent/test_answer_turn.py (history as prior messages, v2 prompt, fresh budget, log block, trimming)"
Task: "Write tests/unit/web_ui/test_chat_api_history.py (UI messages → turns, text only)"
Task: "Extend tests/contract/web_ui/test_chat_endpoint.py (history forwarded to answer_turn)"

# Data in parallel with code:
Task: "Add follow-up / standalone / long-conversation cases to data/testsets/conversations/orcamentos-aeb-csv-conversations.json"
Task: "Create src/qa_agent/prompts/system_v2.md"
```

## Parallel Example: Phase 2

```bash
Task: "Create src/qa_agent/conversation.py (ConversationTurn, ConversationContext)"
Task: "Add ConversationLogContext + AgentRunLogEntry.conversation in src/qa_agent/models.py"
Task: "Add history_char_limit to src/qa_agent/settings.py"
Task: "Add version param to src/qa_agent/prompt_loader.py"
Task: "Generalize _ask_with_retry in src/testset_runner/runner.py"
Task: "Create src/testset_runner/conversation_models.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup → Phase 2 Foundational (proves the standalone path is unchanged, T012).
2. Phase 3 US1 → validate with the offline tests and quickstart.md §2 step 1.
3. **STOP and VALIDATE**: run T037 and check SC-001/SC-004/SC-006 before claiming the feature works.

### Incremental Delivery

1. Setup + Foundational → conversational core and evaluation harness ready.
2. US1 → follow-ups work (MVP).
3. US2 → clarification replies work; re-measure US1 SCs since v2 changed.
4. US3 → isolation verified and fresh-chat cases measured.
5. Polish → docs, regression run, results note.

---

## Notes

- [P] tasks = different files, no dependency on an incomplete task.
- Tests that assert model *quality* are live runner checks (T037, T042, T047), not CI tests.
- Commit after each task or logical group; stop at any checkpoint to validate a story on its own.
