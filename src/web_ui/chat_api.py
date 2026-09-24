"""chat_api: `/api/chat` (contracts/chat-api.md).

Speaks the Vercel AI SDK wire protocol the bundled chat UI expects, using
`pydantic_ai.ui.vercel_ai.VercelAIAdapter` only for parsing the request and encoding the
response (research.md R3) — never for actually running the agent. Dataset selection stays
a deterministic, pre-model-loop step (research.md R1), so the answer itself comes from
`QaAgentQuestionAnswerer.answer`, the same seam `testset_runner` uses, run in a thread pool
since it is a blocking call.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from uuid import uuid4

from pydantic_ai import Agent
from pydantic_ai.ui.vercel_ai import VercelAIAdapter
from pydantic_ai.ui.vercel_ai.request_types import TextUIPart
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

from qa_agent.answerer import QuestionAnswerer
from qa_agent.models import QuestionAnsweringResult

_SDK_VERSION = 7

# Never derived from the caught exception (FR-011): a provider error can embed the
# configured API key (e.g. in a request URL), so the message shown to the browser is
# always this fixed, generic string, never `str(exc)`.
_UNEXPECTED_ERROR_MESSAGE = "Ocorreu um erro inesperado ao processar a pergunta."

# Adapter construction requires an `AbstractAgent`, but `from_request`/`streaming_response`
# never run it — they only parse the request body and encode our own chunks (research.md
# R3) — so a bare, model-less `Agent()` satisfies the type without wiring up the project's
# real agent (which lives behind `QuestionAnswerer.answer`, resolved per question).
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


def _latest_user_question(adapter: VercelAIAdapter) -> str:
    for message in reversed(adapter.run_input.messages):
        if message.role != "user":
            continue
        text = "".join(part.text for part in message.parts if isinstance(part, TextUIPart))
        return text.strip()
    return ""


async def _as_async_iterator(chunks: list[BaseChunk]) -> AsyncIterator[BaseChunk]:
    for chunk in chunks:
        yield chunk


def build_chat_endpoint(answerer: QuestionAnswerer) -> Callable[[Request], Awaitable[Response]]:
    async def chat_endpoint(request: Request) -> Response:
        adapter = await VercelAIAdapter.from_request(request, agent=_ADAPTER_AGENT, sdk_version=_SDK_VERSION)
        try:
            question = _latest_user_question(adapter)
            if question:
                result = await run_in_threadpool(answerer.answer, question)
                chunks = encode_answer_chunks(result)
            else:
                chunks = encode_empty_chunks()
        except Exception:
            chunks = encode_error_chunks(_UNEXPECTED_ERROR_MESSAGE)
        return adapter.streaming_response(_as_async_iterator(chunks))

    return chat_endpoint


async def options_chat(request: Request) -> Response:
    return Response()
