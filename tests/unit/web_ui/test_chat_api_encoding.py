"""Unit tests for `web_ui.chat_api`'s pure chunk-building functions (plan.md Testing section).

No server involved — these test the exact chunk sequence/field values the contract
(contracts/chat-api.md) requires.
"""

from pydantic_ai.ui.vercel_ai.response_types import (
    ErrorChunk,
    FinishChunk,
    StartChunk,
    TextDeltaChunk,
    TextEndChunk,
    TextStartChunk,
)

from qa_agent.models import QuestionAnsweringResult
from web_ui.chat_api import encode_answer_chunks, encode_empty_chunks, encode_error_chunks


def _result(answer: str = "a resposta") -> QuestionAnsweringResult:
    return QuestionAnsweringResult(
        answer=answer,
        dataset_key="orcamentos-aeb-csv",
        outcome="full",
    )


def test_encode_answer_chunks_sequence_and_fields() -> None:
    chunks = encode_answer_chunks(_result("a resposta"))

    assert [type(c) for c in chunks] == [
        StartChunk,
        TextStartChunk,
        TextDeltaChunk,
        TextEndChunk,
        FinishChunk,
    ]

    text_start, text_delta, text_end = chunks[1], chunks[2], chunks[3]
    assert text_delta.delta == "a resposta"
    assert text_start.id == text_delta.id == text_end.id
    assert chunks[-1].finish_reason == "stop"


def test_encode_empty_chunks_is_just_a_finish_chunk() -> None:
    chunks = encode_empty_chunks()

    assert len(chunks) == 1
    assert isinstance(chunks[0], FinishChunk)
    assert chunks[0].finish_reason == "stop"


def test_encode_error_chunks_never_includes_a_secret_it_was_not_given() -> None:
    secret = "sk-super-secret-key"
    chunks = encode_error_chunks("Ocorreu um erro inesperado ao processar a pergunta.")

    assert len(chunks) == 1
    assert isinstance(chunks[0], ErrorChunk)
    assert secret not in chunks[0].error_text
