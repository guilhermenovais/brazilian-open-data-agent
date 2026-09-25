"""CLI: `python -m web_ui.cli` (contracts/cli.md).

Every agent-config flag falls back to the same `QA_AGENT_*` environment variables
`testset_runner.cli` already uses (research.md R5), so a developer who has them exported
for the testset runner gets the web UI "for free". `--host`/`--port` are new to this
command and fall back to `QA_WEB_*` instead, keeping `AgentSettings`'s env prefix scoped to
agent config only. For every flag/env pair, an explicitly-passed flag wins (FR-003).

`--history-char-limit` (008) falls back to `QA_AGENT_HISTORY_CHAR_LIMIT`, then 16000: the
characters of earlier turns sent with each chat message (008 contracts/cli.md).
"""

import argparse
import errno
import os
import socket
import sys

import uvicorn

from qa_agent.answerer import QaAgentQuestionAnswerer
from web_ui.app import create_app
from web_ui.settings import WebServerSettings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="web_ui")
    parser.add_argument("--model")
    parser.add_argument("--base-url")
    parser.add_argument("--api-key")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--history-char-limit")
    return parser


_DEFAULT_HISTORY_CHAR_LIMIT = "16000"


def _parse_history_char_limit(raw: str) -> int | None:
    """The value as an int ≥ 0, or `None` when it is anything else."""
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


def _port_in_use(host: str, port: int) -> bool:
    """An explicit pre-bind check (research.md R6): `uvicorn.run(...)` itself catches its
    own bind `OSError` internally and calls `sys.exit()` directly — it never raises one for
    calling code to catch — so the only way to detect and report a port conflict ourselves
    is to attempt the bind here, first.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((host, port))
        except OSError as exc:
            return exc.errno == errno.EADDRINUSE
    return False


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    model = args.model or os.environ.get("QA_AGENT_MODEL")
    if not model:
        print("Error: --model is required (or set QA_AGENT_MODEL).", file=sys.stderr)
        sys.exit(1)
    base_url = args.base_url or os.environ.get("QA_AGENT_BASE_URL")
    api_key = args.api_key or os.environ.get("QA_AGENT_API_KEY")
    history_char_limit = _parse_history_char_limit(
        args.history_char_limit
        or os.environ.get("QA_AGENT_HISTORY_CHAR_LIMIT")
        or _DEFAULT_HISTORY_CHAR_LIMIT
    )
    if history_char_limit is None:
        print("Error: --history-char-limit must be an integer >= 0.", file=sys.stderr)
        sys.exit(1)

    # Only the flags actually passed are forwarded — `WebServerSettings`'s own
    # env-then-default resolution (pydantic-settings) governs anything left unset,
    # so flag-over-env precedence (FR-003) holds for `--host`/`--port` too.
    if args.host is not None and args.port is not None:
        settings = WebServerSettings(host=args.host, port=args.port)
    elif args.host is not None:
        settings = WebServerSettings(host=args.host)
    elif args.port is not None:
        settings = WebServerSettings(port=args.port)
    else:
        settings = WebServerSettings()

    if _port_in_use(settings.host, settings.port):
        print(f"Error: {settings.host}:{settings.port} is already in use.", file=sys.stderr)
        sys.exit(1)

    answerer = QaAgentQuestionAnswerer(
        model, base_url, api_key=api_key, history_char_limit=history_char_limit
    )
    app = create_app(answerer, host=settings.host)

    print(f"Chat UI available at: http://{settings.host}:{settings.port}")
    print(f"Conversation history limit: {history_char_limit} characters")
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
