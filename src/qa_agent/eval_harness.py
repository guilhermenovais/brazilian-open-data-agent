"""Live-model evaluation harness (research.md §11, quickstart.md "Live-model track").

Not part of the pytest/CI gate — no task wires this into .github/workflows/ci.yml.
Runs `answer_question` against a real, configured model for a fixed, versioned
question set, and records each result alongside the full `AgentSettings` used and a
timestamp, for manual review of the model-quality Success Criteria (SC-001/SC-002/
SC-005) that no scripted test double can validate.

Usage:
    export QA_AGENT_MODEL=openai:gpt-4o-mini
    export OPENAI_API_KEY=...
    python -m qa_agent.eval_harness
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from dataset_selector.briefing import FileBriefingSource
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.selector import StaticDatasetSelector
from dataset_selector.usage_log import JsonlSelectionLogger

from qa_agent.capabilities import answer_question
from qa_agent.run_log import JsonlRunLogger
from qa_agent.settings import AgentSettings

REPO_ROOT = Path(__file__).parent.parent.parent
BRIEFINGS_ROOT = REPO_ROOT / "data" / "briefings"
DATASETS_ROOT = REPO_ROOT / "data" / "datasets"
EVAL_RESULTS_PATH = REPO_ROOT / "data" / "logs" / "qa_agent_eval_results.jsonl"

QUESTIONS = [
    "Quanto foi pago pela AEB em 2015?",
    "Quanto foi gasto pela AEB em 2015?",
    "Quanto o Ministério da Saúde gastou em 2015?",
    "Qual ação teve o maior valor pago em 2015?",
    "Me fale sobre o orçamento.",
]


def main() -> None:
    # model_name has no default by design (research.md §6) — pydantic-settings fills it
    # from QA_AGENT_MODEL at runtime, which pyright can't see from the constructor alone.
    settings = AgentSettings()  # pyright: ignore[reportCallIssue]
    selector = StaticDatasetSelector(
        briefing_source=FileBriefingSource(BRIEFINGS_ROOT),
        locator=LocalDatasetLocator(DATASETS_ROOT),
    )
    selection_logger = JsonlSelectionLogger(REPO_ROOT / "data" / "logs" / "dataset_selections.jsonl")
    run_logger = JsonlRunLogger(REPO_ROOT / "data" / "logs" / "qa_agent_runs.jsonl")

    EVAL_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVAL_RESULTS_PATH.open("a") as f:
        for question in QUESTIONS:
            result = answer_question(
                question,
                selector=selector,
                selection_logger=selection_logger,
                run_logger=run_logger,
                settings=settings,
            )
            record = {
                "question": question,
                "answer": result.answer,
                "dataset_key": result.dataset_key,
                "outcome": result.outcome,
                "settings": settings.model_dump(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"[{result.outcome}] {question}\n  -> {result.answer}\n")


if __name__ == "__main__":
    main()
