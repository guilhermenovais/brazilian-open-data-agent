"""Unit tests for qa_agent.conversation: turn models and fit_history (008 contracts/conversational-answering.md)."""

import pytest
from pydantic import ValidationError

from qa_agent.conversation import ConversationContext, ConversationTurn, fit_history


def _turn(question_len: int, answer_len: int | None = 0) -> ConversationTurn:
    answer = None if answer_len is None else "a" * answer_len
    return ConversationTurn(question="q" * question_len, answer=answer)


def test_turn_rejects_an_empty_question() -> None:
    with pytest.raises(ValidationError):
        ConversationTurn(question="", answer="x")


def test_turn_size_counts_a_missing_answer_as_zero() -> None:
    assert ConversationTurn(question="abc", answer=None).size == 3
    assert ConversationTurn(question="abc", answer="de").size == 5


def test_context_rejects_turn_index_zero() -> None:
    with pytest.raises(ValidationError):
        ConversationContext(conversation_id="c", turn_index=0, history=[])


def test_context_rejects_an_empty_conversation_id() -> None:
    with pytest.raises(ValidationError):
        ConversationContext(conversation_id="", turn_index=1, history=[])


def test_fit_history_of_no_turns_is_empty() -> None:
    assert fit_history([], 1000) == []


def test_fit_history_with_zero_limit_is_empty() -> None:
    assert fit_history([_turn(1, 1)], 0) == []


def test_fit_history_keeps_everything_that_fits() -> None:
    turns = [_turn(5, 5), _turn(5, 5), _turn(5, 5)]
    assert fit_history(turns, 30) == turns


def test_fit_history_returns_the_most_recent_suffix_in_order() -> None:
    turns = [_turn(10, 10), _turn(3, 3), _turn(4, 4)]
    result = fit_history(turns, 15)
    assert result == turns[1:]


def test_fit_history_result_is_maximal() -> None:
    turns = [_turn(5, 5), _turn(5, 5), _turn(5, 5), _turn(5, 5)]
    result = fit_history(turns, 25)
    assert len(result) == 2
    previous = turns[len(turns) - len(result) - 1]
    assert sum(t.size for t in result) + previous.size > 25


def test_fit_history_stops_at_the_first_turn_that_does_not_fit() -> None:
    small_old, large_middle, small_new = _turn(1, 1), _turn(50, 50), _turn(1, 1)
    result = fit_history([small_old, large_middle, small_new], 10)
    assert result == [small_new]


def test_fit_history_drops_everything_when_the_newest_turn_exceeds_the_limit() -> None:
    assert fit_history([_turn(1, 1), _turn(20, 20)], 10) == []


def test_fit_history_never_truncates_text() -> None:
    turns = [_turn(7, None), _turn(3, 4)]
    result = fit_history(turns, 8)
    assert result == [turns[1]]
    assert result[0].question == "qqq"
    assert result[0].answer == "aaaa"
