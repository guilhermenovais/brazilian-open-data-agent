"""chat_api: `/api/chat` (contracts/chat-api.md).

Speaks the Vercel AI SDK wire protocol the bundled chat UI expects, using
`pydantic_ai.ui.vercel_ai.VercelAIAdapter` only for parsing the request and encoding the
response (research.md R3) — never for actually running the agent. Dataset selection stays
a deterministic, pre-model-loop step (research.md R1), so the answer itself comes from
`ConversationalAnswerer.answer_turn`, the same seam `testset_runner`'s conversation runner
uses, run in a thread pool since it is a blocking call.

008 supersedes step 2 of 005's contracts/chat-api.md, where "earlier messages … are
ignored": the earlier visible messages of the request are now turned into conversation
turns (008 contracts/chat-api.md). The server still keeps no conversation state. Each
request's history comes only from its own payload, which is the UI's current view of that
one chat, so chats stay isolated and edits/regenerations are reflected by construction.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from uuid import uuid4

from pydantic_ai import Agent
from pydantic_ai.ui.vercel_ai import VercelAIAdapter
from pydantic_ai.ui.vercel_ai.request_types import (
    RegenerateMessage,
    SubmitMessage,
    TextUIPart,
    UIMessage,
)
from pydantic_ai.ui.vercel_ai.response_types import (
    BaseChunk,
    ErrorChunk,
    FinishChunk,
    StartChunk,
    TextDeltaChunk,
    TextEndChunk,
    TextStartChunk,
)
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response

from qa_agent.answerer import ConversationalAnswerer
from qa_agent.conversation import ConversationContext, ConversationTurn
from qa_agent.models import QuestionAnsweringResult

_SDK_VERSION = 7

# Never derived from the caught exception (FR-011): a provider error can embed the
# configured API key (e.g. in a request URL), so the message shown to the browser is
# always this fixed, generic string, never `str(exc)`.
_UNEXPECTED_ERROR_MESSAGE = "Ocorreu um erro inesperado ao processar a pergunta."

# Adapter construction requires an `AbstractAgent`, but `from_request`/`streaming_response`
# never run it — they only parse the request body and encode our own chunks (research.md
# R3) — so a bare, model-less `Agent()` satisfies the type without wiring up the project's
# real agent (which lives behind `ConversationalAnswerer.answer_turn`, resolved per message).
_ADAPTER_AGENT: Agent = Agent()


def encode_answer_chunks(result: QuestionAnsweringResult) -> list[BaseChunk]:
    text_id = str(uuid4())
    return [
        StartChunk(),
        TextStartChunk(id=text_id),
        TextDeltaChunk(id=text_id, delta=result.answer),
        TextEndChunk(id=text_id),
        FinishChunk(finish_reason="stop"),
    ]


def encode_empty_chunks() -> list[BaseChunk]:
    return [FinishChunk(finish_reason="stop")]


def encode_error_chunks(message: str) -> list[BaseChunk]:
    return [ErrorChunk(error_text=message)]


def _message_text(message: UIMessage) -> str:
    return "".join(part.text for part in message.parts if isinstance(part, TextUIPart)).strip()


def _conversation_from(
    run_input: SubmitMessage | RegenerateMessage,
) -> tuple[str, ConversationContext] | None:
    """The current message and its conversation context, or `None` when there is no
    non-empty user message (008 contracts/chat-api.md step 2, research.md R7).

    The current message is the last user message with text; anything after it is ignored.
    Before it, each non-empty user message opens a turn, and the text of the assistant
    messages that follow becomes that turn's answer (`None` if there is none, e.g. after
    an `ErrorChunk`). Only `TextUIPart` text is read: tool, reasoning, file and source
    parts, `system` messages and assistant text before the first user message are all
    dropped, so only visible text crosses turns (FR-001). Deliberately a plain parse
    rather than `VercelAIAdapter.load_messages`, which would carry every part type.
    """
    messages = run_input.messages
    current_index = next(
        (
            i
            for i in range(len(messages) - 1, -1, -1)
            if messages[i].role == "user" and _message_text(messages[i])
        ),
        None,
    )
    if current_index is None:
        return None

    history: list[ConversationTurn] = []
    question: str | None = None
    answers: list[str] = []
    for message in messages[:current_index]:
        text = _message_text(message)
        if message.role == "user" and text:
            if question is not None:
                history.append(_turn(question, answers))
            question, answers = text, []
        elif message.role == "assistant" and text and question is not None:
            answers.append(text)
    if question is not None:
        history.append(_turn(question, answers))

    context = ConversationContext(
        conversation_id=run_input.id, turn_index=len(history) + 1, history=history
    )
    return _message_text(messages[current_index]), context


def _turn(question: str, answers: list[str]) -> ConversationTurn:
    answer = "\n\n".join(answers).strip()
    return ConversationTurn(question=question, answer=answer or None)


async def _as_async_iterator(chunks: list[BaseChunk]) -> AsyncIterator[BaseChunk]:
    for chunk in chunks:
        yield chunk


def build_chat_endpoint(
    answerer: ConversationalAnswerer,
) -> Callable[[Request], Awaitable[Response]]:
    async def chat_endpoint(request: Request) -> Response:
        adapter = await VercelAIAdapter.from_request(request, agent=_ADAPTER_AGENT, sdk_version=_SDK_VERSION)
        try:
            conversation = _conversation_from(adapter.run_input)
            if conversation is not None:
                message, context = conversation
                result = await run_in_threadpool(answerer.answer_turn, message, context)
                chunks = encode_answer_chunks(result)
            else:
                chunks = encode_empty_chunks()
        except Exception:
            chunks = encode_error_chunks(_UNEXPECTED_ERROR_MESSAGE)
        return adapter.streaming_response(_as_async_iterator(chunks))

    return chat_endpoint


async def options_chat(request: Request) -> Response:
    return Response()
