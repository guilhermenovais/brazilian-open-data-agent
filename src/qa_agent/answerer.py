"""QuestionAnswerer: the seam over `qa_agent.answer_question` (research.md R2).

Lives here rather than under `testset_runner` because `web_ui` is a second consumer with
no dataset-specific logic of its own — a leaf-package cross-import (`web_ui` importing
from `testset_runner`) would be backwards layering, so the seam moved up to `qa_agent`,
where both `testset_runner` and `web_ui` can depend on it directly.

`QaAgentQuestionAnswerer` is built once per run/process from a model/base-url/api-key
target — one `AgentSettings`, one `StaticDatasetSelector`, one selection/run logger pair,
all reused across every question; nothing here carries per-question state. It implements
both `QuestionAnswerer` and `ConversationalAnswerer`; a conversation's history always
arrives with each call, never stored here (008 research.md R1).
"""

from pathlib import Path
from typing import Protocol

from dataset_selector.briefing import FileBriefingSource
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.selector import StaticDatasetSelector
from dataset_selector.usage_log import JsonlSelectionLogger

from data_access.text_matching import TextMatchingConfig
from qa_agent.capabilities import answer_question, answer_turn
from qa_agent.conversation import ConversationContext
from qa_agent.models import QuestionAnsweringResult
from qa_agent.run_log import JsonlRunLogger
from qa_agent.settings import AgentSettings

REPO_ROOT = Path(__file__).parent.parent.parent
DEFAULT_BRIEFINGS_ROOT = REPO_ROOT / "data" / "briefings"
DEFAULT_DATASETS_ROOT = REPO_ROOT / "data" / "datasets"
DEFAULT_SELECTION_LOG_PATH = REPO_ROOT / "data" / "logs" / "dataset_selections.jsonl"
DEFAULT_RUN_LOG_PATH = REPO_ROOT / "data" / "logs" / "qa_agent_runs.jsonl"


class QuestionAnswerer(Protocol):
    def answer(self, question: str) -> QuestionAnsweringResult: ...


class ConversationalAnswerer(Protocol):
    """Answers one message of a conversation, given the earlier visible turns (008).

    Two consumers (Eng. Principle 2): the web UI chat, which rebuilds `context` from the
    browser's payload on every request, and `testset_runner`'s conversation runner, which
    replays scripted conversations turn by turn. Kept separate from `QuestionAnswerer.answer`
    so the standalone contract, and every existing double of it, stays untouched.
    """

    def answer_turn(self, message: str, context: ConversationContext) -> QuestionAnsweringResult: ...


class QaAgentQuestionAnswerer:
    def __init__(
        self,
        model_name: str,
        base_url: str | None = None,
        *,
        api_key: str | None = None,
        briefings_root: str | Path = DEFAULT_BRIEFINGS_ROOT,
        datasets_root: str | Path = DEFAULT_DATASETS_ROOT,
        selection_log_path: str | Path = DEFAULT_SELECTION_LOG_PATH,
        run_log_path: str | Path = DEFAULT_RUN_LOG_PATH,
        history_char_limit: int = 16_000,
        text_matching: TextMatchingConfig = TextMatchingConfig(),
    ) -> None:
        self._settings = AgentSettings(
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            history_char_limit=history_char_limit,
            text_matching=text_matching,
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

    @property
    def history_char_limit(self) -> int:
        """The history limit `answer_turn` applies, so callers can record it."""
        return self._settings.history_char_limit

    @property
    def text_matching(self) -> TextMatchingConfig:
        """The text-matching config the data tools use, so callers can record it (009)."""
        return self._settings.text_matching

    def answer_turn(self, message: str, context: ConversationContext) -> QuestionAnsweringResult:
        return answer_turn(
            message,
            context=context,
            selector=self._selector,
            selection_logger=self._selection_logger,
            run_logger=self._run_logger,
            settings=self._settings,
        )
