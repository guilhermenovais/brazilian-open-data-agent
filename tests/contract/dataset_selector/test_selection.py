"""Contract tests for dataset selection, one per US1/US2 Acceptance Scenario plus
FR-007/SC-005 and the NoBriefingsAvailableError edge case (contracts/selection.md).
"""

from pathlib import Path

import pytest

from dataset_selector.briefing import FileBriefingSource
from dataset_selector.capabilities import select_dataset
from dataset_selector.exceptions import NoBriefingsAvailableError
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.selector import StaticDatasetSelector
from dataset_selector.usage_log import JsonlSelectionLogger

REPO_ROOT = Path(__file__).parent.parent.parent.parent
BRIEFINGS_ROOT = REPO_ROOT / "data" / "briefings"
DATASETS_ROOT = REPO_ROOT / "data" / "datasets"


def _real_selector() -> StaticDatasetSelector:
    return StaticDatasetSelector(
        briefing_source=FileBriefingSource(BRIEFINGS_ROOT),
        locator=LocalDatasetLocator(DATASETS_ROOT),
    )


def test_us1_1_question_about_aeb_budget_resolves_to_orcamentos_aeb_csv(
    tmp_path: Path,
) -> None:
    logger = JsonlSelectionLogger(tmp_path / "log.jsonl")
    result = select_dataset(
        "Quanto foi empenhado pela AEB em 2015?",
        selector=_real_selector(),
        logger=logger,
    )
    assert result.dataset_key == "orcamentos-aeb-csv"
    assert result.briefing != ""
    assert result.dataset.resolve("dados_gerais/tb_geral.csv") == (
        DATASETS_ROOT / "orcamentos-aeb-csv" / "dados_gerais" / "tb_geral.csv"
    )


def test_us1_2_unrelated_question_returns_same_result_as_scenario_1(
    tmp_path: Path,
) -> None:
    logger = JsonlSelectionLogger(tmp_path / "log.jsonl")
    selector = _real_selector()
    result_1 = select_dataset(
        "Quanto foi empenhado pela AEB em 2015?", selector=selector, logger=logger
    )
    result_2 = select_dataset(
        "What's the weather like today?", selector=selector, logger=logger
    )
    assert result_2.dataset_key == result_1.dataset_key
    assert result_2.briefing == result_1.briefing


def test_fr007_sc005_successful_selection_appends_one_log_entry(tmp_path: Path) -> None:
    log_path = tmp_path / "log.jsonl"
    logger = JsonlSelectionLogger(log_path)
    select_dataset("Any question", selector=_real_selector(), logger=logger)

    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    assert '"question"' in lines[0]
    assert '"dataset_key"' in lines[0]
    assert '"timestamp"' in lines[0]


def test_us2_1_briefing_key_resolves_to_matching_dataset_folder() -> None:
    locator = LocalDatasetLocator(DATASETS_ROOT)
    assert locator.locate("orcamentos-aeb-csv") == DATASETS_ROOT / "orcamentos-aeb-csv"


def test_no_briefings_available_raises_and_writes_no_log_entry(tmp_path: Path) -> None:
    empty_briefings = tmp_path / "briefings"
    empty_briefings.mkdir()
    selector = StaticDatasetSelector(
        briefing_source=FileBriefingSource(empty_briefings),
        locator=LocalDatasetLocator(DATASETS_ROOT),
    )
    log_path = tmp_path / "log.jsonl"
    logger = JsonlSelectionLogger(log_path)

    with pytest.raises(NoBriefingsAvailableError):
        select_dataset("Any question", selector=selector, logger=logger)

    assert not log_path.exists()
