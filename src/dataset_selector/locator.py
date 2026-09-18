"""DatasetLocator: resolves a dataset key to its physical folder (research.md §4)."""

from pathlib import Path
from typing import Protocol

from dataset_selector.exceptions import DatasetNotFoundError


class DatasetLocator(Protocol):
    def locate(self, key: str) -> Path: ...


class LocalDatasetLocator:
    def __init__(self, datasets_root: str | Path) -> None:
        self._root = Path(datasets_root)

    def locate(self, key: str) -> Path:
        path = self._root / key
        if not path.is_dir():
            raise DatasetNotFoundError(key)
        return path
