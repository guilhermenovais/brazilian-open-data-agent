"""SC-007 / FR-014 regression: the standalone path's model input is unchanged by 008.

`_answer_with_selection` gained keyword-only `history`, `prompt_version` and `log_context`
parameters for the conversational path. With their defaults, which is how `answer_question`
calls it, the model must still receive exactly one request holding only the question, the
v1 instructions, and the run log must record `"conversation": null`.
"""

import json
from pathlib import Path

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from dataset_selector.briefing import FileBriefingSource
from dataset_selector.capabilities import select_dataset
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.selector import StaticDatasetSelector
from dataset_selector.usage_log import JsonlSelectionLogger
from qa_agent.capabilities import _answer_with_selection
from qa_agent.prompt_loader import render
from qa_agent.run_log import JsonlRunLogger
from qa_agent.settings import AgentSettings

REPO_ROOT = Path(__file__).parent.parent.parent.parent
BRIEFINGS_ROOT = REPO_ROOT / "data" / "briefings"
DATASETS_ROOT = REPO_ROOT / "data" / "datasets"
QUESTION = "Quanto foi pago pela AEB em 2013?"


def test_standalone_call_sends_only_the_question_with_v1_instructions(tmp_path: Path) -> None:
    received: list[tuple[list[ModelMessage], str | None]] = []

    def scripted(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        received.append((list(messages), info.instructions))
        return ModelResponse(parts=[TextPart(json.dumps({"answer": "ok", "outcome": "full"}))])

    selection = select_dataset(
        QUESTION,
        selector=StaticDatasetSelector(
            briefing_source=FileBriefingSource(BRIEFINGS_ROOT),
            locator=LocalDatasetLocator(DATASETS_ROOT),
        ),
        logger=JsonlSelectionLogger(tmp_path / "selections.jsonl"),
    )
    log_path = tmp_path / "runs.jsonl"

    _answer_with_selection(
        QUESTION,
        selection,
        run_logger=JsonlRunLogger(log_path),
        settings=AgentSettings(model_name="test", instrument=False),
        model_override=FunctionModel(scripted),
    )

    assert len(received) == 1
    messages, instructions = received[0]
    assert len(messages) == 1
    request = messages[0]
    assert isinstance(request, ModelRequest)
    user_parts = [p for p in request.parts if isinstance(p, UserPromptPart)]
    assert [p.content for p in user_parts] == [QUESTION]
    # pydantic-ai strips surrounding whitespace from instructions before sending them.
    assert instructions == render(selection.briefing).strip()
    assert render(selection.briefing) == render(selection.briefing, version="v1")

    log_line = json.loads(log_path.read_text().splitlines()[0])
    assert "conversation" in log_line
    assert log_line["conversation"] is None
