"""Contract tests for 006 contracts/failure-details.md: every caught failure in
`answer_question` becomes a redacted, root-cause `FailureDetail` on both the result and
the run log (US1 AS1, AS2, AS4, AS5; US2 classification via FunctionModel).
"""

from pathlib import Path

import pytest
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from dataset_selector.briefing import FileBriefingSource
from dataset_selector.capabilities import select_dataset
from dataset_selector.exceptions import NoBriefingsAvailableError
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.models import DatasetSelectionResult
from dataset_selector.selector import StaticDatasetSelector
from dataset_selector.usage_log import JsonlSelectionLogger
from qa_agent.capabilities import (
    _NO_DATASET_ANSWER,
    _PROCESSING_FAILED_ANSWER,
    _answer_with_selection,
    answer_question,
)
from qa_agent.models import AgentRunLogEntry, QuestionAnsweringResult
from qa_agent.settings import AgentSettings

FIXTURES_ROOT = Path(__file__).parent.parent.parent / "fixtures" / "qa_agent"
UNREADABLE_ROOT = FIXTURES_ROOT / "unreadable_dataset"
SECRET = "sk-test-DO-NOT-LEAK-1234567890"
QUESTION = "Qualquer pergunta"


class RecordingRunLogger:
    def __init__(self) -> None:
        self.entries: list[AgentRunLogEntry] = []

    def log(self, entry: AgentRunLogEntry) -> None:
        self.entries.append(entry)


class RaisingSelector:
    def select(self, question: str) -> DatasetSelectionResult:
        raise NoBriefingsAvailableError()


def _settings() -> AgentSettings:
    return AgentSettings(model_name="test", instrument=False, api_key=SECRET)


def _selection(tmp_path: Path) -> DatasetSelectionResult:
    selector = StaticDatasetSelector(
        briefing_source=FileBriefingSource(UNREADABLE_ROOT / "briefings"),
        locator=LocalDatasetLocator(UNREADABLE_ROOT / "datasets"),
    )
    return select_dataset(
        QUESTION, selector=selector, logger=JsonlSelectionLogger(tmp_path / "selections.jsonl")
    )


def _run_raising(
    tmp_path: Path, make_exc
) -> tuple[QuestionAnsweringResult, RecordingRunLogger]:
    def raising(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise make_exc()

    run_logger = RecordingRunLogger()
    result = _answer_with_selection(
        QUESTION,
        _selection(tmp_path),
        run_logger=run_logger,
        settings=_settings(),
        model_override=FunctionModel(raising),
    )
    return result, run_logger


def _chained(outer: BaseException, inner: BaseException):
    def make() -> BaseException:
        try:
            raise inner
        except BaseException as caught:
            outer.__cause__ = caught
            return outer

    return make


def _assert_logged_once_with_same_failure(
    result: QuestionAnsweringResult, run_logger: RecordingRunLogger
) -> None:
    assert len(run_logger.entries) == 1
    assert run_logger.entries[0].failure == result.failure


# --- US1 ------------------------------------------------------------------------------


def test_http_error_records_the_root_cause_and_keeps_the_answer_text(tmp_path: Path) -> None:
    result, run_logger = _run_raising(
        tmp_path,
        _chained(ModelHTTPError(status_code=401, model_name="test", body=None), RuntimeError("bad key")),
    )

    assert result.errored is True
    assert result.failure is not None
    assert result.failure.type == "RuntimeError"
    assert result.failure.message == "bad key"
    assert result.answer == _PROCESSING_FAILED_ANSWER
    _assert_logged_once_with_same_failure(result, run_logger)


def test_unknown_exception_records_its_type_and_message(tmp_path: Path) -> None:
    result, run_logger = _run_raising(tmp_path, lambda: ValueError("boom"))

    assert result.failure is not None
    assert result.failure.type == "ValueError"
    assert result.failure.message == "boom"
    _assert_logged_once_with_same_failure(result, run_logger)


def test_a_provider_echoing_the_api_key_never_leaks_it(tmp_path: Path) -> None:
    result, run_logger = _run_raising(
        tmp_path, lambda: RuntimeError(f"Incorrect API key provided: {SECRET}")
    )

    assert result.failure is not None
    assert "DO-NOT-LEAK" not in result.failure.message
    logged = run_logger.entries[0].failure
    assert logged is not None
    assert "DO-NOT-LEAK" not in logged.message
    assert "DO-NOT-LEAK" not in run_logger.entries[0].model_dump_json()


def test_dataset_selection_failure_is_described_and_never_transient(tmp_path: Path) -> None:
    run_logger = RecordingRunLogger()
    result = answer_question(
        QUESTION,
        selector=RaisingSelector(),
        selection_logger=JsonlSelectionLogger(tmp_path / "selections.jsonl"),
        run_logger=run_logger,
        settings=_settings(),
    )

    assert result.errored is True
    assert result.failure is not None
    assert result.failure.type == "NoBriefingsAvailableError"
    assert result.failure.transient is False
    assert result.answer == _NO_DATASET_ANSWER
    _assert_logged_once_with_same_failure(result, run_logger)


def test_normal_completion_carries_no_failure(tmp_path: Path) -> None:
    def answering(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart('{"answer": "Não sei.", "outcome": "none"}')])

    run_logger = RecordingRunLogger()
    result = _answer_with_selection(
        QUESTION,
        _selection(tmp_path),
        run_logger=run_logger,
        settings=_settings(),
        model_override=FunctionModel(answering),
    )

    assert result.errored is False
    assert result.failure is None
    _assert_logged_once_with_same_failure(result, run_logger)


# --- US2: transient classification through answer_question ---------------------------


def _http(status_code: int, retry_after: str | None = None):
    headers = {"retry-after": retry_after} if retry_after is not None else None
    return lambda: ModelHTTPError(
        status_code=status_code, model_name="test", body=None, headers=headers
    )


def test_rate_limit_with_retry_after_is_transient_and_carries_the_wait(tmp_path: Path) -> None:
    result, _ = _run_raising(tmp_path, _http(429, retry_after="30"))

    assert result.failure is not None
    assert result.failure.transient is True
    assert result.failure.retry_after_seconds == 30.0


@pytest.mark.parametrize(
    "make_exc,transient",
    [
        (_http(503), True),
        (_http(401), False),
        (_http(404), False),
        (lambda: ModelAPIError(model_name="test", message="Connection error."), True),
        (lambda: ValueError("boom"), False),
    ],
    ids=["503", "401", "404", "ModelAPIError", "ValueError"],
)
def test_agent_failures_are_classified(tmp_path: Path, make_exc, transient: bool) -> None:
    result, _ = _run_raising(tmp_path, make_exc)

    assert result.failure is not None
    assert result.failure.transient is transient


def test_wrapped_timeout_is_transient_and_reports_the_root_type(tmp_path: Path) -> None:
    result, _ = _run_raising(
        tmp_path, _chained(RuntimeError("wrapper"), TimeoutError("read timed out"))
    )

    assert result.failure is not None
    assert result.failure.transient is True
    assert result.failure.type == "TimeoutError"
