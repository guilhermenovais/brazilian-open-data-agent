# Quickstart: Validating Conversational Context

This guide validates the feature end to end. Interfaces are in [contracts/](./contracts/)
and models are in [data-model.md](./data-model.md).

## Prerequisites

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
export QA_AGENT_MODEL=openai:gpt-4o-mini     # or --model / --base-url for OpenRouter / vLLM
export OPENAI_API_KEY=...                      # live-model tracks only
```

## 1. Offline track (CI gate, no model calls)

```bash
pytest tests/contract tests/unit -v
pyright src/
```

| Scenario | Test | Expected |
|---|---|---|
| Whole-turn, oldest-first trimming (FR-011) | `tests/unit/qa_agent/test_conversation.py` | suffix / maximal / whole-turn / `limit=0` cases pass |
| UI payload → turns, text only (FR-001, FR-010) | `tests/unit/web_ui/test_chat_api_history.py` | tool/reasoning parts dropped, reply-less user turn has `answer=None`, messages after the last user message ignored |
| History reaches the model as prior messages, v2 prompt (FR-001/002) | `tests/contract/qa_agent/test_answer_turn.py` | the `FunctionModel` receives prior `UserPromptPart`/`TextPart` pairs and no tool parts from earlier turns |
| Fresh budget per turn (FR-009) | same | a turn after a 10-step turn still gets 10 steps |
| Log carries conversation id / turn index (FR-013) | same | a JSONL line with a `conversation` block; standalone lines have `null` |
| Standalone path unchanged (FR-014, SC-007) | `tests/contract/qa_agent/test_standalone_unchanged.py` | `answer_question` model input: no history, v1 instructions |
| Chat endpoint forwards history, chats isolated (FR-007/008) | `tests/contract/web_ui/test_chat_endpoint.py` | two payloads with different `id`s produce contexts containing only their own messages |
| Conversation runner replays, scores, saves (FR-015) | `tests/contract/testset_runner/test_run_conversations.py` | a fake answerer sees growing history, scoring follows the table, the run file round-trips |
| Existing retry behavior intact | `tests/contract/testset_runner/test_retry.py` | unchanged tests pass |

## 2. Manual web UI check (US1–US3)

```bash
python -m web_ui.cli --history-char-limit 16000
# → Chat UI available at: http://127.0.0.1:8000
# → Conversation history limit: 16000 characters
```

In one chat:

1. "Quanto foi pago pela Agência Espacial Brasileira em 2010?" then "e em 2011?". The second
   answer gives the 2011 paid amount (R$ 108.537.469) without asking for more context
   (US1-AS1). The AEB has rows only for 2000–2013, so a 2015/2016 AEB question is correctly
   declined.
2. "Me fale sobre o orçamento." The agent asks for something more specific. Reply
   "o valor pago pela AEB em 2011": the answer is the 2011 paid amount (US2-AS1).
3. Open a **new chat** and send "e em 2016?". The agent says the question is too vague
   (US3-AS1).
4. `tail -n 3 data/logs/qa_agent_runs.jsonl` shows `conversation.conversation_id` equal to
   each chat's URL id, with `turn_index` 1, 2, … (FR-013).

## 3. Live-model evaluation track (SC-001 to SC-006; not in CI)

```bash
python -m testset_runner.cli run-conversations \
  --testset data/testsets/conversations/orcamentos-aeb-csv-conversations.json \
  --history-char-limit 16000
```

Read the result from the report and from `data/conversation_runs/<run_id>.json`
(`summary.by_category`):

| Criterion | Where to read it | Pass when |
|---|---|---|
| SC-001 | `follow-up-year`, `follow-up-metric`, `follow-up-reference` match rate | ≥ 90% |
| SC-002 | `clarification` match rate on reply turns | ≥ 90% |
| SC-003 | `turns_with_ungrounded_figures`, then record a `derived` / `ungrounded` verdict for each flagged figure in `results.md` | 0 `ungrounded` verdicts |
| SC-004 | `standalone-after-unrelated` match rate | 100% |
| SC-005 | `fresh-chat-follow-up` match rate (`expected_outcome: none`) | 100% |
| SC-006 | `long-conversation`: `by_status.errored`, and each turn's `history_turns_used` vs `history_turns_sent` in the run file | 0 errored; used == sent on every turn at the default limit |

To check trimming under pressure (FR-011), re-run with `--history-char-limit 500`. Every
turn should still be answered, and late turns in the run file should show
`history_turns_used < history_turns_sent` (the run log's `history_turns_dropped > 0` agrees).

## 4. Regression check for the standalone runner (SC-007)

```bash
python -m testset_runner.cli run --testset data/testsets/orcamentos-aeb-csv-10.json
```

The run succeeds with the same report format as before. The offline test
`test_standalone_unchanged.py` is the deterministic proof that the model input is
identical. Live match rates can still vary between runs because of model nondeterminism.
