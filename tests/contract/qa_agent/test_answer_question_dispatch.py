"""Contract tests closing two coverage gaps found by /speckit-analyze:

- C1: every other contract test drives `_answer_with_selection` directly, having
  already run `select_dataset` itself — `answer_question`'s own
  try/select_dataset/except dispatch to `_answer_with_selection` (capabilities.py)
  was never exercised on the success path. This test drives the real public
  `answer_question` entry point (contracts/answering.md) on a real, successful
  selection and confirms it delegates to `_answer_with_selection` with exactly
  what it received and returns that result unchanged.
- C2: FR-012's/FR-011's "every question is an independent request... without
  depending on hidden state carried over from a previous, separate question"
  was only guaranteed structurally (a fresh `StepBudget`/`AgentDeps` is built
  per call), with no executable assertion. This test runs two questions back
  to back through `_answer_with_selection` and confirms their `StepBudget`s are
  distinct instances with independent counters.
"""

import json
from pathlib import Path

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

import qa_agent.capabilities as qa_capabilities
from dataset_selector.briefing import FileBriefingSource
from dataset_selector.capabilities import select_dataset
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.selector import StaticDatasetSelector
from dataset_selector.usage_log import JsonlSelectionLogger
from qa_agent.capabilities import _answer_with_selection, answer_question
from qa_agent.deps import AgentDeps
from qa_agent.run_log import JsonlRunLogger
from qa_agent.settings import AgentSettings

REPO_ROOT = Path(__file__).parent.parent.parent.parent
BRIEFINGS_ROOT = REPO_ROOT / "data" / "briefings"
DATASETS_ROOT = REPO_ROOT / "data" / "datasets"
DATASET_KEY = "orcamentos-aeb-csv"
QUESTION = "Quanto foi pago pela AEB em 2013?"


def _real_selector() -> StaticDatasetSelector:
    return StaticDatasetSelector(
        briefing_source=FileBriefingSource(BRIEFINGS_ROOT),
        locator=LocalDatasetLocator(DATASETS_ROOT),
    )


def test_answer_question_dispatches_to_answer_with_selection_on_success(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, object] = {}
    sentinel = object()

    def fake_answer_with_selection(question, selection, *, run_logger, settings, **_kwargs):
        captured["question"] = question
        captured["selection"] = selection
        captured["run_logger"] = run_logger
        captured["settings"] = settings
        return sentinel

    monkeypatch.setattr(qa_capabilities, "_answer_with_selection", fake_answer_with_selection)

    run_logger = JsonlRunLogger(tmp_path / "runs.jsonl")
    settings = AgentSettings(model_name="test", instrument=False)

    result = answer_question(
        QUESTION,
        selector=_real_selector(),
        selection_logger=JsonlSelectionLogger(tmp_path / "selections.jsonl"),
        run_logger=run_logger,
        settings=settings,
    )

    assert result is sentinel
    assert captured["question"] == QUESTION
    assert captured["selection"].dataset_key == DATASET_KEY
    assert captured["run_logger"] is run_logger
    assert captured["settings"] is settings


def _scripted_single_tool_call_then_answer():
    def scripted(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if len(messages) == 1:
            return ModelResponse(parts=[ToolCallPart(tool_name="discover_data_sources", args={})])
        return ModelResponse(parts=[TextPart(json.dumps({"answer": "ok", "outcome": "full"}))])

    return scripted


def test_sequential_calls_do_not_share_step_budget_state(tmp_path: Path) -> None:
    selector = _real_selector()
    run_logger = JsonlRunLogger(tmp_path / "runs.jsonl")
    settings = AgentSettings(model_name="test", instrument=False)
    model = FunctionModel(_scripted_single_tool_call_then_answer())

    deps_by_call: list[AgentDeps] = []
    for _ in range(2):
        selection = select_dataset(
            QUESTION,
            selector=selector,
            logger=JsonlSelectionLogger(tmp_path / "selections.jsonl"),
        )
        _answer_with_selection(
            QUESTION,
            selection,
            run_logger=run_logger,
            settings=settings,
            model_override=model,
            capture_deps=deps_by_call,
        )

    assert len(deps_by_call) == 2
    first_budget, second_budget = deps_by_call[0].step_budget, deps_by_call[1].step_budget
    assert first_budget is not second_budget
    assert first_budget.attempts == 1
    assert second_budget.attempts == 1
