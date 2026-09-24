"""Unit tests for `web_ui.cli`'s flag/env precedence and error paths (research.md R5/R6).

Mirrors `tests/unit/testset_runner/test_cli.py`'s pattern of monkeypatching the
underlying call and asserting on captured arguments — no real server is bound.
"""

import pytest

import web_ui.cli as cli_module
from web_ui.cli import build_parser, main


def _run(monkeypatch, argv: list[str]) -> tuple[int, list[str]]:
    """Run `main()` with `argv`, capturing the (model, base_url, api_key) `create_app` /
    `QaAgentQuestionAnswerer` was actually built with, and returns (exit_code, printed_lines).

    `uvicorn.run` is stubbed to a no-op so nothing actually binds a socket.
    """
    captured: dict[str, object] = {}

    def fake_answerer(model_name, base_url=None, *, api_key=None):
        captured["model_name"] = model_name
        captured["base_url"] = base_url
        captured["api_key"] = api_key
        return object()

    def fake_create_app(answerer, host):
        captured["host"] = host
        return object()

    def fake_uvicorn_run(app, host, port):
        captured["run_host"] = host
        captured["run_port"] = port

    monkeypatch.setattr(cli_module, "QaAgentQuestionAnswerer", fake_answerer)
    monkeypatch.setattr(cli_module, "create_app", fake_create_app)
    monkeypatch.setattr(cli_module.uvicorn, "run", fake_uvicorn_run)
    monkeypatch.setattr(cli_module, "_port_in_use", lambda host, port: False)
    monkeypatch.setattr("sys.argv", ["web_ui", *argv])

    exit_code = 0
    try:
        main()
    except SystemExit as exc:
        exit_code = exc.code or 0

    return exit_code, captured


def test_explicit_flags_are_used_when_no_env_vars_are_set(monkeypatch) -> None:
    for var in ("QA_AGENT_MODEL", "QA_AGENT_BASE_URL", "QA_AGENT_API_KEY", "QA_WEB_HOST", "QA_WEB_PORT"):
        monkeypatch.delenv(var, raising=False)

    exit_code, captured = _run(
        monkeypatch,
        ["--model", "gpt-4o-mini", "--base-url", "http://localhost:8000/v1", "--api-key", "sk-test"],
    )

    assert exit_code == 0
    assert captured["model_name"] == "gpt-4o-mini"
    assert captured["base_url"] == "http://localhost:8000/v1"
    assert captured["api_key"] == "sk-test"


def test_env_vars_are_used_when_flags_are_omitted(monkeypatch) -> None:
    monkeypatch.setenv("QA_AGENT_MODEL", "env-model")
    monkeypatch.setenv("QA_AGENT_BASE_URL", "http://env-host/v1")
    monkeypatch.delenv("QA_AGENT_API_KEY", raising=False)

    exit_code, captured = _run(monkeypatch, [])

    assert exit_code == 0
    assert captured["model_name"] == "env-model"
    assert captured["base_url"] == "http://env-host/v1"
    assert captured["api_key"] is None


def test_flag_overrides_env_var_for_the_same_setting(monkeypatch) -> None:
    monkeypatch.setenv("QA_AGENT_MODEL", "env-model")

    exit_code, captured = _run(monkeypatch, ["--model", "flag-model"])

    assert exit_code == 0
    assert captured["model_name"] == "flag-model"


def test_missing_model_exits_1_and_never_builds_a_server(monkeypatch, capsys) -> None:
    monkeypatch.delenv("QA_AGENT_MODEL", raising=False)

    exit_code, captured = _run(monkeypatch, [])

    assert exit_code == 1
    assert "create_app" not in captured
    assert "Error: --model is required (or set QA_AGENT_MODEL)." in capsys.readouterr().err


def test_explicit_host_and_port_are_reflected_in_the_printed_url(monkeypatch, capsys) -> None:
    monkeypatch.setenv("QA_AGENT_MODEL", "gpt-4o-mini")
    monkeypatch.delenv("QA_WEB_HOST", raising=False)
    monkeypatch.delenv("QA_WEB_PORT", raising=False)

    exit_code, captured = _run(monkeypatch, ["--host", "0.0.0.0", "--port", "9000"])

    assert exit_code == 0
    assert captured["host"] == "0.0.0.0"
    assert captured["run_host"] == "0.0.0.0"
    assert captured["run_port"] == 9000
    assert "Chat UI available at: http://0.0.0.0:9000" in capsys.readouterr().out


def test_web_env_vars_are_used_when_host_and_port_flags_are_omitted(monkeypatch) -> None:
    monkeypatch.setenv("QA_AGENT_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("QA_WEB_HOST", "0.0.0.0")
    monkeypatch.setenv("QA_WEB_PORT", "9001")

    exit_code, captured = _run(monkeypatch, [])

    assert exit_code == 0
    assert captured["host"] == "0.0.0.0"
    assert captured["run_port"] == 9001


def test_port_in_use_prints_a_clear_error_and_exits_1(monkeypatch, capsys) -> None:
    # `uvicorn.run(...)` itself swallows a bind `OSError` and calls `sys.exit()` directly
    # (confirmed by reading `uvicorn/server.py`) — it never raises one for `cli.py` to
    # catch — so `main()` detects the conflict via its own pre-bind check (`_port_in_use`)
    # instead of wrapping `uvicorn.run(...)` in a try/except.
    monkeypatch.setenv("QA_AGENT_MODEL", "gpt-4o-mini")
    monkeypatch.delenv("QA_WEB_HOST", raising=False)
    monkeypatch.delenv("QA_WEB_PORT", raising=False)

    def fake_answerer(model_name, base_url=None, *, api_key=None):
        return object()

    def fake_create_app(answerer, host):
        return object()

    def fake_uvicorn_run_should_not_be_called(app, host, port):
        raise AssertionError("uvicorn.run must not be reached when the port is already in use")

    def fake_port_in_use(host, port):
        assert (host, port) == ("127.0.0.1", 8000)
        return True

    monkeypatch.setattr(cli_module, "QaAgentQuestionAnswerer", fake_answerer)
    monkeypatch.setattr(cli_module, "create_app", fake_create_app)
    monkeypatch.setattr(cli_module.uvicorn, "run", fake_uvicorn_run_should_not_be_called)
    monkeypatch.setattr(cli_module, "_port_in_use", fake_port_in_use)
    monkeypatch.setattr("sys.argv", ["web_ui", "--port", "8000"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert "Error: 127.0.0.1:8000 is already in use." in capsys.readouterr().err


def test_port_in_use_is_detected_via_a_real_bind_attempt(monkeypatch) -> None:
    """Unlike the test above (which stubs `_port_in_use` to isolate `main()`'s branching),
    this exercises the real socket-bind check against an actual bound port — the scenario
    that motivated abandoning the `except OSError` approach around `uvicorn.run(...)`.
    """
    import socket as socket_module

    holder = socket_module.socket(socket_module.AF_INET, socket_module.SOCK_STREAM)
    holder.bind(("127.0.0.1", 0))
    holder.listen(1)
    bound_port = holder.getsockname()[1]
    try:
        assert cli_module._port_in_use("127.0.0.1", bound_port) is True
    finally:
        holder.close()


def test_build_parser_accepts_all_contract_flags() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "--model",
            "m",
            "--base-url",
            "http://x",
            "--api-key",
            "k",
            "--host",
            "0.0.0.0",
            "--port",
            "1234",
        ]
    )

    assert args.model == "m"
    assert args.base_url == "http://x"
    assert args.api_key == "k"
    assert args.host == "0.0.0.0"
    assert args.port == 1234
