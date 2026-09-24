"""Unit test for cli.py's `run` subcommand flag wiring (US3, research.md §9)."""

from datetime import datetime, timezone
from pathlib import Path

import testset_runner.cli as cli_module
from testset_runner.cli import build_parser
import pytest

from testset_runner.models import (
    RetryPolicy,
    RunComparison,
    RunSummary,
    TargetConfiguration,
    Testset,
    TestRun,
)


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

    def fake_run_testset(testset_path, target, *, answerer, store, matcher=None, retry_policy=None):
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

    def fake_run_testset(testset_path, target, *, answerer, store, matcher=None, retry_policy=None):
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


# --- 006: failure-type report lines -----------------------------------------------


def _summary(**overrides) -> RunSummary:
    fields: dict = dict(
        total_questions=6,
        match_rate=0.0,
        by_status={"errored": 4, "matched": 2},
        by_category={},
        target_unreachable=False,
        errored_by_failure_type={"AuthenticationError": 1, "ConnectError": 3},
    )
    fields.update(overrides)
    return RunSummary(**fields)


def _run_cli_with_summary(monkeypatch, tmp_path: Path, capsys, summary: RunSummary) -> str:
    for var in ("QA_AGENT_MODEL", "QA_AGENT_BASE_URL", "QA_AGENT_API_KEY", "QA_AGENT_MAX_ATTEMPTS"):
        monkeypatch.delenv(var, raising=False)

    def fake_run_testset(testset_path, target, *, answerer, store, matcher=None, **kwargs):
        run = _fake_run(target)
        return run.model_copy(update={"summary": summary})

    monkeypatch.setattr(cli_module, "run_testset", fake_run_testset)
    args = build_parser().parse_args(
        ["run", "--testset", "t.json", "--model", "m", "--out-dir", str(tmp_path)]
    )
    assert args.func(args) == 0
    return capsys.readouterr().out


def test_run_prints_errored_counts_per_failure_type_most_common_first(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    out = _run_cli_with_summary(monkeypatch, tmp_path, capsys, _summary())

    lines = out.splitlines()
    header = lines.index("Errored by failure type:")
    assert lines[header + 1 : header + 3] == ["  ConnectError: 3", "  AuthenticationError: 1"]
    assert "Most common failure" not in out


def test_run_names_the_most_common_failure_after_the_unreachable_warning(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    out = _run_cli_with_summary(
        monkeypatch, tmp_path, capsys, _summary(target_unreachable=True)
    )

    lines = out.splitlines()
    warning = next(i for i, line in enumerate(lines) if line.startswith("WARNING"))
    assert lines[warning + 1] == "Most common failure: ConnectError (3 questions)"


def test_run_omits_the_failure_type_block_when_nothing_errored(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    out = _run_cli_with_summary(
        monkeypatch,
        tmp_path,
        capsys,
        _summary(by_status={"matched": 6}, errored_by_failure_type={}),
    )

    assert "Errored by failure type:" not in out


def test_run_prints_retried_and_exhausted_question_counts(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    out = _run_cli_with_summary(
        monkeypatch, tmp_path, capsys, _summary(retried_questions=4, errored_after_retries=1)
    )

    lines = out.splitlines()
    assert "Questions retried: 4" in lines
    assert "Errored after exhausting retries: 1" in lines
    assert lines.index("Errored after exhausting retries: 1") < lines.index(
        "Errored by failure type:"
    )


def test_run_prints_not_recorded_for_missing_retry_counts(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    out = _run_cli_with_summary(monkeypatch, tmp_path, capsys, _summary())

    assert "Questions retried: not recorded" in out
    assert "Errored after exhausting retries: not recorded" in out



# --- 006 US3: --max-attempts and the recorded policy ------------------------------------


def _invoke_run(monkeypatch, tmp_path: Path, extra: list[str]) -> tuple[int, dict]:
    for var in ("QA_AGENT_BASE_URL", "QA_AGENT_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    captured: dict[str, object] = {}

    def fake_run_testset(testset_path, target, *, answerer, store, matcher=None, retry_policy=None):
        captured["retry_policy"] = retry_policy
        return _fake_run(target).model_copy(update={"retry_policy": retry_policy})

    monkeypatch.setattr(cli_module, "run_testset", fake_run_testset)
    args = build_parser().parse_args(
        ["run", "--testset", "t.json", "--model", "m", "--out-dir", str(tmp_path), *extra]
    )
    return args.func(args), captured


def test_max_attempts_flag_sets_the_retry_policy(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("QA_AGENT_MAX_ATTEMPTS", raising=False)
    exit_code, captured = _invoke_run(monkeypatch, tmp_path, ["--max-attempts", "5"])
    assert exit_code == 0
    assert captured["retry_policy"] == RetryPolicy(max_attempts=5)


def test_max_attempts_falls_back_to_the_env_var(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QA_AGENT_MAX_ATTEMPTS", "2")
    _, captured = _invoke_run(monkeypatch, tmp_path, [])
    assert captured["retry_policy"] == RetryPolicy(max_attempts=2)


def test_max_attempts_defaults_to_three(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("QA_AGENT_MAX_ATTEMPTS", raising=False)
    _, captured = _invoke_run(monkeypatch, tmp_path, [])
    assert captured["retry_policy"] == RetryPolicy(max_attempts=3)


@pytest.mark.parametrize(
    "flag_value,env_value",
    [("0", None), ("-1", None), ("abc", None), (None, "0")],
    ids=["zero", "negative", "not-a-number", "env-zero"],
)
def test_invalid_max_attempts_is_rejected_before_running(
    monkeypatch, tmp_path: Path, capsys, flag_value: str | None, env_value: str | None
) -> None:
    if env_value is None:
        monkeypatch.delenv("QA_AGENT_MAX_ATTEMPTS", raising=False)
    else:
        monkeypatch.setenv("QA_AGENT_MAX_ATTEMPTS", env_value)
    extra = [f"--max-attempts={flag_value}"] if flag_value is not None else []

    exit_code, captured = _invoke_run(monkeypatch, tmp_path, extra)

    assert exit_code == 1
    assert "Error: --max-attempts must be an integer >= 1." in capsys.readouterr().err
    assert captured == {}


def test_run_prints_the_retry_policy(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.delenv("QA_AGENT_MAX_ATTEMPTS", raising=False)
    _invoke_run(monkeypatch, tmp_path, [])
    assert "Retry policy: max_attempts=3, waits 2.0s x2.0 (cap 60.0s)" in capsys.readouterr().out


def test_compare_prints_each_runs_retry_policy_or_not_recorded(monkeypatch, capsys) -> None:
    comparison = RunComparison(
        run_a=TargetConfiguration(model_name="a"),
        run_b=TargetConfiguration(model_name="b"),
        entries=[],
        summary={},
        retry_policy_a=None,
        retry_policy_b=RetryPolicy(max_attempts=3),
    )
    monkeypatch.setattr(cli_module, "compare_runs", lambda a, b, *, store: comparison)
    args = build_parser().parse_args(["compare", "a.json", "b.json"])

    assert args.func(args) == 0

    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("Run A:")
    assert lines[1] == "  retry policy: not recorded"
    assert lines[2].startswith("Run B:")
    assert lines[3] == "  retry policy: max_attempts=3, waits 2.0s x2.0 (cap 60.0s)"
