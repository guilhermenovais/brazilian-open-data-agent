"""Contract test for the new `steps`/`errored` fields on `QuestionAnsweringResult`
(data-model.md, research.md §3/§10).

Mirrors test_multi_step.py's pattern against the real bundled dataset: a scripted
multi-tool-call run must produce a non-empty `result.steps` with correct
`tool_name`/`arguments`/`result_summary` per step, and a separate scripted
model-call failure must produce `result.errored is True`.
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
from qa_agent.capabilities import _answer_with_selection
from qa_agent.run_log import JsonlRunLogger
from qa_agent.settings import AgentSettings

REPO_ROOT = Path(__file__).parent.parent.parent.parent
BRIEFINGS_ROOT = REPO_ROOT / "data" / "briefings"
DATASETS_ROOT = REPO_ROOT / "data" / "datasets"
SOURCE_IDENTIFIER = "dados_gerais/tb_geral.csv"
AEB_UNIT_NAME = "Agência Espacial Brasileira"
QUESTION_YEAR = "2013"


def _real_selector() -> StaticDatasetSelector:
    return StaticDatasetSelector(
        briefing_source=FileBriefingSource(BRIEFINGS_ROOT),
        locator=LocalDatasetLocator(DATASETS_ROOT),
    )


def _select(question: str, tmp_path: Path):
    return select_dataset(
        question,
        selector=_real_selector(),
        logger=JsonlSelectionLogger(tmp_path / "selections.jsonl"),
    )


def test_steps_are_extracted_with_tool_name_arguments_and_result_summary(tmp_path: Path) -> None:
    def scripted(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if len(messages) == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="query_rows",
                        args={
                            "identifier": SOURCE_IDENTIFIER,
                            "filters": [
                                {"field": "nome_unidade", "op": "equals", "value": AEB_UNIT_NAME},
                                {"field": "data_ano", "op": "equals", "value": QUESTION_YEAR},
                            ],
                        },
                    )
                ]
            )
        answer = "O total pago pela AEB em 2013 foi consultado."
        return ModelResponse(parts=[TextPart(json.dumps({"answer": answer, "outcome": "full"}))])

    selection = _select("Quanto foi pago pela AEB em 2013?", tmp_path)
    result = _answer_with_selection(
        "Quanto foi pago pela AEB em 2013?",
        selection,
        run_logger=JsonlRunLogger(tmp_path / "runs.jsonl"),
        settings=AgentSettings(model_name="test", instrument=False),
        model_override=FunctionModel(scripted),
    )

    assert result.errored is False
    assert len(result.steps) >= 1
    step = result.steps[0]
    assert step.tool_name == "query_rows"
    assert step.arguments["identifier"] == SOURCE_IDENTIFIER
    assert isinstance(step.result_summary, str)
    assert step.result_summary != ""


def test_model_call_failure_sets_errored_true(tmp_path: Path) -> None:
    def raising(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise RuntimeError("simulated provider failure")

    selection = _select("Qualquer pergunta", tmp_path)
    result = _answer_with_selection(
        "Qualquer pergunta",
        selection,
        run_logger=JsonlRunLogger(tmp_path / "runs.jsonl"),
        settings=AgentSettings(model_name="test", instrument=False),
        model_override=FunctionModel(raising),
    )

    assert result.errored is True
    assert result.steps == []
    assert result.outcome == "none"
