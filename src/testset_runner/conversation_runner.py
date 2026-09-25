"""run_conversations: replays scripted conversations through the conversational path (008 FR-015).

Each conversation is replayed turn by turn through `ConversationalAnswerer.answer_turn`,
the same seam the web UI chat uses. For turn k, the history is the scripted messages
1..k-1 paired with the agent's **actual** answers from this run, which is exactly what the
chat would have shown and sent back. Trimming and prompting happen inside `qa_agent`; this
module only records what `fit_history` kept, using the same pure function.

The standalone `run_testset` path is untouched: this is a second mode with its own models
and store, reusing the retry loop and the numeric matcher (contracts/conversation-testset.md).
"""

import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from qa_agent.answerer import ConversationalAnswerer
from qa_agent.capabilities import CONVERSATION_PROMPT_VERSION
from qa_agent.conversation import ConversationContext, ConversationTurn, fit_history
from qa_agent.models import FailureDetail, QuestionAnsweringResult
from testset_runner.conversation_loader import ConversationTestsetLoader
from testset_runner.conversation_models import (
    ConversationResult,
    ConversationRun,
    ConversationRunSummary,
    ScriptedTurn,
    TurnResult,
    TurnStatus,
)
from testset_runner.grounding import ungrounded_figures
from testset_runner.matcher import MatchStrategy, NumericMatchStrategy
from testset_runner.models import RetryPolicy, TargetConfiguration
from testset_runner.runner import _RUN_ID_FORMAT, _UNKNOWN_DATASET_KEY, _ask_with_retry
from testset_runner.store import ConversationRunStore

Grade = Literal["matched", "not_matched", "needs_review"]
_GRADE_ORDER: dict[Grade, int] = {"not_matched": 0, "needs_review": 1, "matched": 2}


def run_conversations(
    testset_path: str | Path,
    target: TargetConfiguration,
    *,
    answerer: ConversationalAnswerer,
    store: ConversationRunStore,
    history_char_limit: int,
    prompt_version: str = CONVERSATION_PROMPT_VERSION,
    matcher: MatchStrategy = NumericMatchStrategy(),
    retry_policy: RetryPolicy = RetryPolicy(),
    sleep: Callable[[float], None] = time.sleep,
) -> ConversationRun:
    """Replays every scripted conversation, scores its turns, and saves one `ConversationRun`.

    `history_char_limit` must equal the answerer's own configured limit (the CLI builds
    both from one value): it is only used to record `history_turns_used`, which then equals
    what the model actually received. A `TestsetLoadError` propagates and nothing is saved.

    Every conversation starts from an empty history (SC-005), and every turn is a fresh
    `answer_turn` call, hence a fresh step budget (FR-009). An errored turn does not stop
    its conversation: its failure text goes into the history, as it would in the chat.
    """
    testset = ConversationTestsetLoader().load(testset_path)
    run_id = datetime.now(timezone.utc).strftime(_RUN_ID_FORMAT)

    results: list[ConversationResult] = []
    for conversation in testset.conversations:
        history: list[ConversationTurn] = []
        turn_results: list[TurnResult] = []
        for k, turn in enumerate(conversation.turns, start=1):
            context = ConversationContext(
                conversation_id=f"{run_id}:{conversation.id}",
                turn_index=k,
                history=list(history),
            )
            result, attempts, failed_attempts = _ask_with_retry(
                lambda: answerer.answer_turn(turn.message, context), retry_policy, sleep
            )
            turn_results.append(
                _turn_result(
                    k,
                    turn,
                    result,
                    attempts=attempts,
                    failed_attempts=failed_attempts,
                    history_turns_sent=len(context.history),
                    history_turns_used=len(fit_history(context.history, history_char_limit)),
                    matcher=matcher,
                )
            )
            history.append(ConversationTurn(question=turn.message, answer=result.answer))
        results.append(
            ConversationResult(
                conversation_id=conversation.id,
                category=conversation.category,
                turns=turn_results,
            )
        )

    run = ConversationRun(
        run_id=run_id,
        created_at=datetime.now(timezone.utc),
        testset=testset,
        target=target,
        retry_policy=retry_policy,
        history_char_limit=history_char_limit,
        prompt_version=prompt_version,
        results=results,
        summary=_summarize(results),
    )
    store.save(run)
    return run


def _turn_result(
    k: int,
    turn: ScriptedTurn,
    result: QuestionAnsweringResult,
    *,
    attempts: int,
    failed_attempts: list[FailureDetail],
    history_turns_sent: int,
    history_turns_used: int,
    matcher: MatchStrategy,
) -> TurnResult:
    return TurnResult(
        turn_index=k,
        message=turn.message,
        expected=turn.expected,
        expected_outcome=turn.expected_outcome,
        actual_answer=result.answer,
        agent_outcome=result.outcome,
        dataset_key=result.dataset_key,
        steps=result.steps,
        history_turns_sent=history_turns_sent,
        history_turns_used=history_turns_used,
        scored=turn.is_scored,
        status=_score(turn, result, matcher),
        ungrounded_figures=(
            [] if result.errored else ungrounded_figures(result.answer, turn.message, result.steps)
        ),
        attempts=attempts,
        failed_attempts=failed_attempts,
        failure=result.failure if result.errored else None,
    )


def _score(turn: ScriptedTurn, result: QuestionAnsweringResult, matcher: MatchStrategy) -> TurnStatus:
    """`errored`, else `unscored`, else the worst of the numeric grade and the exact
    outcome check (`not_matched` < `needs_review` < `matched`)."""
    if result.errored:
        return "errored"
    if not turn.is_scored:
        return "unscored"
    grades: list[Grade] = []
    if turn.expected is not None:
        grades.append(matcher.evaluate(turn.expected, result.answer))
    if turn.expected_outcome is not None:
        grades.append("matched" if result.outcome == turn.expected_outcome else "not_matched")
    return min(grades, key=lambda grade: _GRADE_ORDER[grade])


def _summarize(results: list[ConversationResult]) -> ConversationRunSummary:
    by_category: dict[str, ConversationRunSummary] = {}
    for category in sorted({r.category for r in results}):
        cat_results = [r for r in results if r.category == category]
        by_category[category] = _tally(cat_results, by_category={}, target_unreachable=False)

    turns = [t for r in results for t in r.turns]
    eligible = [t for t in turns if t.dataset_key != _UNKNOWN_DATASET_KEY]
    target_unreachable = bool(eligible) and all(t.status == "errored" for t in eligible)

    return _tally(results, by_category=by_category, target_unreachable=target_unreachable)


def _tally(
    results: list[ConversationResult],
    *,
    by_category: dict[str, ConversationRunSummary],
    target_unreachable: bool,
) -> ConversationRunSummary:
    turns = [t for r in results for t in r.turns]
    by_status: dict[str, int] = {}
    for t in turns:
        by_status[t.status] = by_status.get(t.status, 0) + 1
    scored = [t for t in turns if t.scored]
    matched = sum(1 for t in scored if t.status == "matched")
    return ConversationRunSummary(
        total_conversations=len(results),
        total_turns=len(turns),
        scored_turns=len(scored),
        match_rate=matched / len(scored) if scored else 0.0,
        by_status=by_status,
        by_category=by_category,
        turns_with_ungrounded_figures=sum(1 for t in turns if t.ungrounded_figures),
        target_unreachable=target_unreachable,
    )
