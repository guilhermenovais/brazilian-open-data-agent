"""QuestionAnswerer: the seam over `qa_agent.answer_question` (research.md §1).

`QaAgentQuestionAnswerer` is built once per run from a `TargetConfiguration` — one
`AgentSettings`, one `StaticDatasetSelector`, one selection/run logger pair, all
reused across every question in the run; nothing here carries per-question state.
"""

from pathlib import Path
from typing import Protocol

from dataset_selector.briefing import FileBriefingSource
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.selector import StaticDatasetSelector
from dataset_selector.usage_log import JsonlSelectionLogger

from qa_agent.capabilities import answer_question
from qa_agent.models import QuestionAnsweringResult
from qa_agent.run_log import JsonlRunLogger
from qa_agent.settings import AgentSettings

from testset_runner.models import TargetConfiguration

REPO_ROOT = Path(__file__).parent.parent.parent
DEFAULT_BRIEFINGS_ROOT = REPO_ROOT / "data" / "briefings"
DEFAULT_DATASETS_ROOT = REPO_ROOT / "data" / "datasets"
DEFAULT_SELECTION_LOG_PATH = REPO_ROOT / "data" / "logs" / "dataset_selections.jsonl"
DEFAULT_RUN_LOG_PATH = REPO_ROOT / "data" / "logs" / "qa_agent_runs.jsonl"


class QuestionAnswerer(Protocol):
    def answer(self, question: str) -> QuestionAnsweringResult: ...


class QaAgentQuestionAnswerer:
    def __init__(
        self,
        target: TargetConfiguration,
        *,
        api_key: str | None = None,
        briefings_root: str | Path = DEFAULT_BRIEFINGS_ROOT,
        datasets_root: str | Path = DEFAULT_DATASETS_ROOT,
        selection_log_path: str | Path = DEFAULT_SELECTION_LOG_PATH,
        run_log_path: str | Path = DEFAULT_RUN_LOG_PATH,
    ) -> None:
        self._settings = AgentSettings(
            model_name=target.model_name,
            base_url=target.base_url,
            api_key=api_key,
        )
        self._selector = StaticDatasetSelector(
            briefing_source=FileBriefingSource(briefings_root),
            locator=LocalDatasetLocator(datasets_root),
        )
        self._selection_logger = JsonlSelectionLogger(selection_log_path)
        self._run_logger = JsonlRunLogger(run_log_path)

    def answer(self, question: str) -> QuestionAnsweringResult:
        return answer_question(
            question,
            selector=self._selector,
            selection_logger=self._selection_logger,
            run_logger=self._run_logger,
            settings=self._settings,
        )
