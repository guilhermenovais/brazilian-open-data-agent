"""html: serves the bundled pydantic-ai chat UI HTML (research.md R4).

Fetched once, on first request, from the same CDN URL `pydantic_ai.ui._web.create_web_app`
uses by default, then cached in memory for the life of the process. An in-memory,
fetch-once cache — rather than `pydantic_ai.ui._web`'s own filesystem-persisted cache — is
enough here: this is a single local dev process, not something restarted often enough for
a disk cache to pay for itself.
"""

import asyncio

import httpx
from starlette.requests import Request
from starlette.responses import Response

# Same URL `pydantic_ai.ui._web.app.DEFAULT_HTML_URL` points at by default (CHAT_UI_VERSION
# 2.1.0). Hardcoded rather than imported from that private (`_web`) subpackage, consistent
# with research.md R4's stance of not depending on its internals.
_CHAT_UI_HTML_URL = "https://cdn.jsdelivr.net/npm/@pydantic/ai-chat-ui@2.1.0/dist/index.html"

_cached_html: bytes | None = None
_fetch_lock = asyncio.Lock()


async def _get_ui_html() -> bytes:
    global _cached_html
    if _cached_html is not None:
        return _cached_html
    async with _fetch_lock:
        if _cached_html is None:
            async with httpx.AsyncClient() as client:
                response = await client.get(_CHAT_UI_HTML_URL)
                response.raise_for_status()
                _cached_html = response.content
    return _cached_html


async def serve_chat_ui(request: Request) -> Response:
    content = await _get_ui_html()
    return Response(content=content, media_type="text/html")
