"""DatasetSelector: chooses which dataset answers a question (research.md §2)."""

from typing import Protocol

from data_access.dataset import Dataset
from dataset_selector.briefing import BriefingSource
from dataset_selector.exceptions import NoBriefingsAvailableError
from dataset_selector.locator import DatasetLocator
from dataset_selector.models import DatasetSelectionResult


class DatasetSelector(Protocol):
    def select(self, question: str) -> DatasetSelectionResult: ...


class StaticDatasetSelector:
    def __init__(self, briefing_source: BriefingSource, locator: DatasetLocator) -> None:
        self._briefing_source = briefing_source
        self._locator = locator

    def select(self, question: str) -> DatasetSelectionResult:
        keys = self._briefing_source.list_keys()
        if not keys:
            raise NoBriefingsAvailableError()
        key = sorted(keys)[0]
        return DatasetSelectionResult(
            dataset_key=key,
            briefing=self._briefing_source.get(key),
            dataset=Dataset(self._locator.locate(key)),
        )
