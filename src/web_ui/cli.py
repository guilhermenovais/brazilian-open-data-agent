"""CLI: `python -m web_ui.cli` (contracts/cli.md).

Every agent-config flag falls back to the same `QA_AGENT_*` environment variables
`testset_runner.cli` already uses (research.md R5), so a developer who has them exported
for the testset runner gets the web UI "for free". `--host`/`--port` are new to this
command and fall back to `QA_WEB_*` instead, keeping `AgentSettings`'s env prefix scoped to
agent config only. For every flag/env pair, an explicitly-passed flag wins (FR-003).
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
    return parser


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

    answerer = QaAgentQuestionAnswerer(model, base_url, api_key=api_key)
    app = create_app(answerer, host=settings.host)

    print(f"Chat UI available at: http://{settings.host}:{settings.port}")
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
