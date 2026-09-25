"""RunLogger: records one entry per answer_question or answer_turn call (FR-013).

Mirrors dataset_selector/usage_log.py's SelectionLogger/JsonlSelectionLogger exactly.
"""

from pathlib import Path
from typing import Protocol

from qa_agent.models import AgentRunLogEntry


class RunLogger(Protocol):
    def log(self, entry: AgentRunLogEntry) -> None: ...


class JsonlRunLogger:
    def __init__(self, log_path: str | Path) -> None:
        self._path = Path(log_path)

    def log(self, entry: AgentRunLogEntry) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a") as f:
            f.write(entry.model_dump_json() + "\n")
