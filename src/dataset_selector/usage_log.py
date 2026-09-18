"""SelectionLogger: records usage data for each selection decision (research.md §7).

Named usage_log.py, not logging.py, to avoid shadowing the stdlib module.
"""

from pathlib import Path
from typing import Protocol

from dataset_selector.models import DatasetSelectionLogEntry


class SelectionLogger(Protocol):
    def log(self, entry: DatasetSelectionLogEntry) -> None: ...


class JsonlSelectionLogger:
    def __init__(self, log_path: str | Path) -> None:
        self._path = Path(log_path)

    def log(self, entry: DatasetSelectionLogEntry) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a") as f:
            f.write(entry.model_dump_json() + "\n")
