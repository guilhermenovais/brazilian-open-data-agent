"""Unit tests for `web_ui.chat_api._conversation_from` (008 contracts/chat-api.md step 2)."""

from pydantic import TypeAdapter

from pydantic_ai.ui.vercel_ai.request_types import RequestData

from qa_agent.conversation import ConversationTurn
from web_ui.chat_api import _conversation_from

_REQUEST = TypeAdapter(RequestData)


def _msg(role: str, *parts: dict, msg_id: str = "m") -> dict:
    return {"id": msg_id, "role": role, "parts": list(parts)}


def _text(text: str) -> dict:
    return {"type": "text", "text": text}


def _parse(messages: list[dict], *, trigger: str = "submit-message", chat_id: str = "chat-1"):
    return _conversation_from(_REQUEST.validate_python({"id": chat_id, "trigger": trigger, "messages": messages}))


def test_the_contract_example() -> None:
    result = _parse(
        [
            _msg("user", _text("Quanto foi pago pela AEB em 2015?")),
            _msg("assistant", _text("Em 2015, o valor pago foi de R$ …")),
            _msg("user", _text("e em 2016?")),
        ]
    )

    assert result is not None
    message, context = result
    assert message == "e em 2016?"
    assert context.conversation_id == "chat-1"
    assert context.turn_index == 2
    assert context.history == [
        ConversationTurn(question="Quanto foi pago pela AEB em 2015?", answer="Em 2015, o valor pago foi de R$ …")
    ]


def test_a_single_message_has_no_history() -> None:
    message, context = _parse([_msg("user", _text("  Quanto foi pago em 2015?  "))])  # type: ignore[misc]
    assert message == "Quanto foi pago em 2015?"
    assert context.history == []
    assert context.turn_index == 1


def test_the_last_non_empty_user_message_is_current_and_later_messages_are_ignored() -> None:
    message, context = _parse(  # type: ignore[misc]
        [
            _msg("user", _text("primeira")),
            _msg("assistant", _text("resposta 1")),
            _msg("user", _text("atual")),
            _msg("assistant", _text("resposta parcial que já existe")),
            _msg("user", _text("   ")),
        ]
    )
    assert message == "atual"
    assert context.history == [ConversationTurn(question="primeira", answer="resposta 1")]


def test_several_assistant_texts_are_joined_and_stripped() -> None:
    _, context = _parse(  # type: ignore[misc]
        [
            _msg("user", _text("q1")),
            _msg("assistant", _text(" parte "), _text("A ")),
            _msg("assistant", _text("parte B")),
            _msg("user", _text("q2")),
        ]
    )
    assert context.history[0].answer == "parte A\n\nparte B"


def test_a_user_message_with_no_reply_gets_no_answer() -> None:
    _, context = _parse(  # type: ignore[misc]
        [_msg("user", _text("q1")), _msg("user", _text("q2")), _msg("assistant", _text("r2")), _msg("user", _text("q3"))]
    )
    assert context.history == [
        ConversationTurn(question="q1", answer=None),
        ConversationTurn(question="q2", answer="r2"),
    ]
    assert context.turn_index == 3


def test_non_text_parts_system_messages_and_leading_assistant_text_are_dropped() -> None:
    _, context = _parse(  # type: ignore[misc]
        [
            _msg("assistant", _text("boas-vindas antes de qualquer pergunta")),
            _msg("system", _text("instrução de sistema")),
            _msg(
                "user",
                _text("q1"),
                {"type": "file", "mediaType": "text/plain", "url": "data:text/plain,x"},
            ),
            _msg(
                "assistant",
                {"type": "reasoning", "text": "pensando..."},
                {
                    "type": "tool-aggregate_rows",
                    "toolCallId": "t1",
                    "state": "output-available",
                    "input": {},
                    "output": {"value": 99},
                },
                _text("resposta final"),
            ),
            _msg("user", _text("q2")),
        ]
    )
    assert context.history == [ConversationTurn(question="q1", answer="resposta final")]


def test_no_non_empty_user_message_returns_none() -> None:
    assert _parse([_msg("user", _text("   "))]) is None
    assert _parse([_msg("assistant", _text("oi"))]) is None
    assert _parse([]) is None


def test_a_regenerate_payload_reflects_only_its_current_messages() -> None:
    """FR-010: the client slices the list before the regenerated reply, so the discarded
    version never appears and the payload is the history."""
    message, context = _parse(  # type: ignore[misc]
        [
            _msg("user", _text("Quanto foi pago em 2015?")),
            _msg("assistant", _text("R$ 10")),
            _msg("user", _text("e em 2016?")),
        ],
        trigger="regenerate-message",
        chat_id="chat-9",
    )
    assert message == "e em 2016?"
    assert context.conversation_id == "chat-9"
    assert context.history == [ConversationTurn(question="Quanto foi pago em 2015?", answer="R$ 10")]
