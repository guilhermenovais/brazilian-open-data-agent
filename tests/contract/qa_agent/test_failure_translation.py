"""Contract tests for US4 Acceptance Scenarios 1-2, covering all three failure tiers
from contracts/errors.md.
"""

import json
from pathlib import Path

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from dataset_selector.briefing import FileBriefingSource
from dataset_selector.capabilities import select_dataset
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.selector import StaticDatasetSelector
from dataset_selector.usage_log import JsonlSelectionLogger
from qa_agent.capabilities import _answer_with_selection, answer_question
from qa_agent.run_log import JsonlRunLogger
from qa_agent.settings import AgentSettings

FIXTURES_ROOT = Path(__file__).parent.parent.parent / "fixtures" / "qa_agent"
NO_BRIEFINGS_ROOT = FIXTURES_ROOT / "no_briefings"
UNREADABLE_ROOT = FIXTURES_ROOT / "unreadable_dataset"
UNREADABLE_BRIEFINGS = UNREADABLE_ROOT / "briefings"
UNREADABLE_DATASETS = UNREADABLE_ROOT / "datasets"


def test_tier1_no_briefings_never_calls_the_model(tmp_path: Path) -> None:
    empty_selector = StaticDatasetSelector(
        briefing_source=FileBriefingSource(NO_BRIEFINGS_ROOT),
        locator=LocalDatasetLocator(NO_BRIEFINGS_ROOT),
    )
    log_path = tmp_path / "runs.jsonl"

    result = answer_question(
        "Quanto foi pago pela AEB em 2015?",
        selector=empty_selector,
        selection_logger=JsonlSelectionLogger(tmp_path / "selections.jsonl"),
        run_logger=JsonlRunLogger(log_path),
        settings=AgentSettings(model_name="test", instrument=False),
    )

    assert result.outcome == "none"
    answer_lower = result.answer.lower()
    assert "não" in answer_lower
    assert "traceback" not in answer_lower
    assert "error" not in answer_lower
    assert str(NO_BRIEFINGS_ROOT) not in result.answer

    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["outcome"] == "none"


def test_tier2_unreadable_source_recovers_into_a_normal_final_answer(tmp_path: Path) -> None:
    selector = StaticDatasetSelector(
        briefing_source=FileBriefingSource(UNREADABLE_BRIEFINGS),
        locator=LocalDatasetLocator(UNREADABLE_DATASETS),
    )
    selection = select_dataset(
        "Quais dados existem?",
        selector=selector,
        logger=JsonlSelectionLogger(tmp_path / "selections.jsonl"),
    )

    call_count = {"n": 0}

    def scripted(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ModelResponse(
                parts=[ToolCallPart(tool_name="inspect_schema", args={"identifier": "broken.csv"})]
            )
        return ModelResponse(
            parts=[
                TextPart(
                    json.dumps(
                        {
                            "answer": (
                                "Não foi possível ler esta fonte de dados no momento; "
                                "não consigo responder com base nela."
                            ),
                            "outcome": "none",
                        }
                    )
                )
            ]
        )

    run_logger = JsonlRunLogger(tmp_path / "runs.jsonl")
    result = _answer_with_selection(
        "Quais dados existem?",
        selection,
        run_logger=run_logger,
        settings=AgentSettings(model_name="test", instrument=False),
        model_override=FunctionModel(scripted),
    )

    answer_lower = result.answer.lower()
    assert "broken.csv" not in answer_lower
    assert "unreadablesourceerror" not in answer_lower
    assert str(UNREADABLE_DATASETS) not in result.answer

    lines = (tmp_path / "runs.jsonl").read_text().splitlines()
    assert len(lines) == 1


def test_tier3_catastrophic_model_failure_never_presents_a_guessed_result(tmp_path: Path) -> None:
    def raising_after_prompt(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise RuntimeError("simulated provider network failure")

    selector = StaticDatasetSelector(
        briefing_source=FileBriefingSource(UNREADABLE_BRIEFINGS),
        locator=LocalDatasetLocator(UNREADABLE_DATASETS),
    )
    selection = select_dataset(
        "Qualquer pergunta",
        selector=selector,
        logger=JsonlSelectionLogger(tmp_path / "selections.jsonl"),
    )
    log_path = tmp_path / "runs.jsonl"
    run_logger = JsonlRunLogger(log_path)

    result = _answer_with_selection(
        "Qualquer pergunta",
        selection,
        run_logger=run_logger,
        settings=AgentSettings(model_name="test", instrument=False),
        model_override=FunctionModel(raising_after_prompt),
    )

    assert result.outcome == "none"
    assert "não foi possível processar" in result.answer.lower()

    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["outcome"] == "none"
