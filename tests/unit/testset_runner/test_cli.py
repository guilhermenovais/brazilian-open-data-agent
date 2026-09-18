"""Unit test for cli.py's `run` subcommand flag wiring (US3, research.md §9)."""

from datetime import datetime, timezone
from pathlib import Path

import testset_runner.cli as cli_module
from testset_runner.cli import build_parser
from testset_runner.models import RunSummary, TargetConfiguration, Testset, TestRun


def _fake_run(target: TargetConfiguration) -> TestRun:
    return TestRun(
        run_id="20260918T153000000000Z",
        created_at=datetime.now(timezone.utc),
        testset=Testset(path="some/testset.json", content_hash="abc", questions=[]),
        target=target,
        results=[],
        summary=RunSummary(
            total_questions=0,
            match_rate=0.0,
            by_status={},
            by_category={},
            target_unreachable=False,
        ),
    )


def test_run_subcommand_accepts_explicit_flags_without_env_vars(monkeypatch, tmp_path: Path) -> None:
    for var in ("QA_AGENT_MODEL", "QA_AGENT_BASE_URL", "QA_AGENT_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    captured: dict[str, object] = {}

    def fake_run_testset(testset_path, target, *, answerer, store, matcher=None):
        captured["testset_path"] = testset_path
        captured["target"] = target
        return _fake_run(target)

    monkeypatch.setattr(cli_module, "run_testset", fake_run_testset)

    parser = build_parser()
    args = parser.parse_args(
        [
            "run",
            "--testset",
            "some/testset.json",
            "--model",
            "gpt-4o-mini",
            "--base-url",
            "http://localhost:8000/v1",
            "--api-key",
            "sk-test",
            "--out-dir",
            str(tmp_path),
        ]
    )

    exit_code = args.func(args)

    assert exit_code == 0
    assert captured["testset_path"] == "some/testset.json"
    target = captured["target"]
    assert isinstance(target, TargetConfiguration)
    assert target.model_name == "gpt-4o-mini"
    assert target.base_url == "http://localhost:8000/v1"


def test_run_subcommand_falls_back_to_env_vars_when_flags_are_omitted(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QA_AGENT_MODEL", "env-model")
    monkeypatch.setenv("QA_AGENT_BASE_URL", "http://env-host/v1")
    monkeypatch.delenv("QA_AGENT_API_KEY", raising=False)

    captured: dict[str, object] = {}

    def fake_run_testset(testset_path, target, *, answerer, store, matcher=None):
        captured["target"] = target
        return _fake_run(target)

    monkeypatch.setattr(cli_module, "run_testset", fake_run_testset)

    parser = build_parser()
    args = parser.parse_args(
        ["run", "--testset", "some/testset.json", "--out-dir", str(tmp_path)]
    )

    exit_code = args.func(args)

    assert exit_code == 0
    target = captured["target"]
    assert isinstance(target, TargetConfiguration)
    assert target.model_name == "env-model"
    assert target.base_url == "http://env-host/v1"


def test_run_subcommand_requires_a_model(monkeypatch, tmp_path: Path) -> None:
    for var in ("QA_AGENT_MODEL", "QA_AGENT_BASE_URL", "QA_AGENT_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    parser = build_parser()
    args = parser.parse_args(["run", "--testset", "some/testset.json", "--out-dir", str(tmp_path)])

    exit_code = args.func(args)

    assert exit_code == 1
