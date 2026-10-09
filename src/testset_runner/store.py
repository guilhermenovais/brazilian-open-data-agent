"""RunStore: persists and reloads a `TestRun` as one JSON file per run (research.md §7).

`ConversationRunStore` does the same for a `ConversationRun` (008).
"""

from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from testset_runner.conversation_models import ConversationRun
from testset_runner.exceptions import RunLoadError
from testset_runner.models import TestRun


class RunStore(Protocol):
    def save(self, run: TestRun) -> str: ...

    def load(self, path: str | Path) -> TestRun: ...


class JsonFileRunStore:
    def __init__(self, out_dir: str | Path) -> None:
        self._out_dir = Path(out_dir)

    def save(self, run: TestRun) -> str:
        self._out_dir.mkdir(parents=True, exist_ok=True)
        path = self._out_dir / f"{run.run_id}.json"
        path.write_text(run.model_dump_json(indent=2))
        return str(path)

    def load(self, path: str | Path) -> TestRun:
        file_path = Path(path)
        try:
            raw = file_path.read_text()
        except OSError as exc:
            raise RunLoadError(f"Could not read run file at {file_path}: {exc}") from exc
        try:
            return TestRun.model_validate_json(raw)
        except ValidationError as exc:
            raise RunLoadError(f"Run file at {file_path} is not a valid TestRun: {exc}") from exc


class ConversationRunStore(Protocol):
    def save(self, run: ConversationRun) -> str: ...

    def load(self, path: str | Path) -> ConversationRun: ...


class JsonFileConversationRunStore:
    def __init__(self, out_dir: str | Path) -> None:
        self._out_dir = Path(out_dir)

    def save(self, run: ConversationRun) -> str:
        self._out_dir.mkdir(parents=True, exist_ok=True)
        path = self._out_dir / f"{run.run_id}.json"
        path.write_text(run.model_dump_json(indent=2))
        return str(path)

    def load(self, path: str | Path) -> ConversationRun:
        file_path = Path(path)
        try:
            raw = file_path.read_text()
        except OSError as exc:
            raise RunLoadError(f"Could not read run file at {file_path}: {exc}") from exc
        try:
            return ConversationRun.model_validate_json(raw)
        except ValidationError as exc:
            raise RunLoadError(
                f"Run file at {file_path} is not a valid ConversationRun: {exc}"
            ) from exc
