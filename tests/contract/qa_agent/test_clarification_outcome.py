"""Contract tests for 008: the `needs_clarification` outcome through the real
`_answer_with_selection` flow (scripted model, real briefing and dataset), plus the prompt
version and briefing fingerprint carried on each result.
"""

from pathlib import Path

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from dataset_selector.briefing import FileBriefingSource
from dataset_selector.capabilities import select_dataset
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.selector import StaticDatasetSelector
from dataset_selector.usage_log import JsonlSelectionLogger
from qa_agent.capabilities import _answer_with_selection
from qa_agent.models import AgentAnswer
from qa_agent.run_log import JsonlRunLogger
from qa_agent.settings import AgentSettings

REPO_ROOT = Path(__file__).parent.parent.parent.parent
BRIEFINGS_ROOT = REPO_ROOT / "data" / "briefings"
DATASETS_ROOT = REPO_ROOT / "data" / "datasets"
AMBIGUOUS_QUESTION = "Qual o valor do orçamento da AEB em 2005?"
CLARIFYING_ANSWER = "Você quer saber o valor autorizado, empenhado, liquidado ou pago?"


def _selection(question: str, tmp_path: Path):
    selector = StaticDatasetSelector(
        briefing_source=FileBriefingSource(BRIEFINGS_ROOT),
        locator=LocalDatasetLocator(DATASETS_ROOT),
    )
    return select_dataset(
        question, selector=selector, logger=JsonlSelectionLogger(tmp_path / "selections.jsonl")
    )


def _clarifying_model() -> FunctionModel:
    """Answers straight away with a clarifying question — no tool call at all."""

    def scripted(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        answer = AgentAnswer(answer=CLARIFYING_ANSWER, outcome="needs_clarification")
        return ModelResponse(parts=[TextPart(answer.model_dump_json())])

    return FunctionModel(scripted)


def test_008_us1_3_scripted_clarification_with_zero_tool_calls(tmp_path: Path) -> None:
    result = _answer_with_selection(
        AMBIGUOUS_QUESTION,
        _selection(AMBIGUOUS_QUESTION, tmp_path),
        run_logger=JsonlRunLogger(tmp_path / "runs.jsonl"),
        settings=AgentSettings(model_name="test", instrument=False),
        model_override=_clarifying_model(),
    )

    assert result.outcome == "needs_clarification"
    assert result.errored is False
    assert result.steps == []
    assert result.answer == CLARIFYING_ANSWER


def test_008_us1_agent_answer_accepts_needs_clarification() -> None:
    answer = AgentAnswer.model_validate({"answer": "...", "outcome": "needs_clarification"})
    assert answer.outcome == "needs_clarification"


# --- 008 US4: prompt version and briefing fingerprint ---------------------------------

import pytest  # noqa: E402

import qa_agent.answerer as answerer_module  # noqa: E402
import qa_agent.capabilities as capabilities_module  # noqa: E402
from qa_agent.answerer import QaAgentQuestionAnswerer  # noqa: E402
from qa_agent.capabilities import answer_question  # noqa: E402
from qa_agent.exceptions import UnknownPromptVersionError  # noqa: E402
from qa_agent.prompt_loader import fingerprint  # noqa: E402


def test_008_us4_3_answerer_rejects_unknown_version(monkeypatch) -> None:
    def must_not_be_built(*args, **kwargs):
        raise AssertionError("nothing may be built for an unknown prompt version")

    for name in ("StaticDatasetSelector", "JsonlSelectionLogger", "JsonlRunLogger", "AgentSettings"):
        monkeypatch.setattr(answerer_module, name, must_not_be_built)

    with pytest.raises(UnknownPromptVersionError):
        QaAgentQuestionAnswerer("m", prompt_version="v9")


def test_008_us4_answerer_exposes_resolved_version(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("QA_AGENT_PROMPT_VERSION", raising=False)
    logs = {
        "selection_log_path": tmp_path / "selections.jsonl",
        "run_log_path": tmp_path / "runs.jsonl",
    }
    assert QaAgentQuestionAnswerer("m", prompt_version="v1", **logs).prompt_version == "v1"
    assert QaAgentQuestionAnswerer("m", **logs).prompt_version == "v2"


def test_008_us4_6_result_carries_briefing_fingerprint(monkeypatch, tmp_path: Path) -> None:
    selection = _selection(AMBIGUOUS_QUESTION, tmp_path)
    rendered_with: list[str] = []
    real_render = capabilities_module.render

    def spy_render(briefing: str, version: str) -> str:
        rendered_with.append(version)
        return real_render(briefing, version)

    monkeypatch.setattr(capabilities_module, "render", spy_render)
    settings = AgentSettings(model_name="test", instrument=False, prompt_version="v1")

    result = _answer_with_selection(
        AMBIGUOUS_QUESTION,
        selection,
        run_logger=JsonlRunLogger(tmp_path / "runs.jsonl"),
        settings=settings,
        model_override=_clarifying_model(),
    )
    assert result.briefing_fingerprint == fingerprint(selection.briefing)
    assert rendered_with == ["v1"]

    def failing(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise RuntimeError("boom")

    errored = _answer_with_selection(
        AMBIGUOUS_QUESTION,
        selection,
        run_logger=JsonlRunLogger(tmp_path / "runs.jsonl"),
        settings=settings,
        model_override=FunctionModel(failing),
    )
    assert errored.errored is True
    assert errored.briefing_fingerprint == fingerprint(selection.briefing)


def test_008_selection_failure_has_no_fingerprint(tmp_path: Path) -> None:
    empty_briefings = REPO_ROOT / "tests" / "fixtures" / "qa_agent" / "no_briefings"
    selector = StaticDatasetSelector(
        briefing_source=FileBriefingSource(empty_briefings),
        locator=LocalDatasetLocator(DATASETS_ROOT),
    )

    result = answer_question(
        AMBIGUOUS_QUESTION,
        selector=selector,
        selection_logger=JsonlSelectionLogger(tmp_path / "selections.jsonl"),
        run_logger=JsonlRunLogger(tmp_path / "runs.jsonl"),
        settings=AgentSettings(model_name="test", instrument=False),
    )

    assert result.errored is True
    assert result.briefing_fingerprint is None
