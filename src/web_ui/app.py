"""app: Starlette app factory wiring `html.py` + `chat_api.py` (research.md R1).

`create_app` builds a custom app rather than mounting `pydantic_ai.ui._web.create_web_app`
unmodified: that helper fixes one static `deps`/`instructions` pair for the whole process,
but this project resolves the dataset (and therefore the briefing/`AgentDeps`) per question,
deterministically, before any model call — a static `deps` would either hard-code one
dataset or push selection into the model's tool-calling loop, both unacceptable
(Constitution Principle VI). Serving the same bundled UI HTML and speaking the same wire
protocol keeps the frontend unmodified; only the chat logic underneath is custom.
"""

import ipaddress
from urllib.parse import urlsplit

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from qa_agent.answerer import QuestionAnswerer
from web_ui import chat_api, html


def _is_allowed_host(hostname: str, configured_host: str) -> bool:
    if hostname in (configured_host, "localhost"):
        return True
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return True


class HostValidationMiddleware:
    """Refuses any `Host` header other than the configured bind host, an IP literal, or
    `localhost` — a DNS-rebinding guard (research.md R4). Reimplemented directly, as a
    single header comparison, rather than importing `pydantic_ai.ui._web`'s private
    `HostValidationMiddleware`.
    """

    def __init__(self, app: ASGIApp, host: str) -> None:
        self.app = app
        self.host = host

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        host_header = headers.get(b"host", b"").decode("latin-1")
        hostname = urlsplit(f"//{host_header}").hostname or ""

        if _is_allowed_host(hostname, self.host):
            await self.app(scope, receive, send)
            return

        response = PlainTextResponse(f"Host {host_header!r} is not allowed.", status_code=421)
        await response(scope, receive, send)


def create_app(answerer: QuestionAnswerer, host: str) -> Starlette:
    routes = [
        Route("/", html.serve_chat_ui, methods=["GET"]),
        Route("/{id}", html.serve_chat_ui, methods=["GET"]),
        Route("/api/chat", chat_api.build_chat_endpoint(answerer), methods=["POST"]),
        Route("/api/chat", chat_api.options_chat, methods=["OPTIONS"]),
    ]
    middleware = [Middleware(HostValidationMiddleware, host=host)]
    return Starlette(routes=routes, middleware=middleware)
