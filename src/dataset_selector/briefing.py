"""BriefingSource: reads briefing content and enumerates keys (research.md §5)."""

from pathlib import Path
from typing import Protocol

from dataset_selector.exceptions import BriefingNotFoundError


class BriefingSource(Protocol):
    def list_keys(self) -> list[str]: ...

    def get(self, key: str) -> str: ...


class FileBriefingSource:
    def __init__(self, briefings_root: str | Path) -> None:
        self._root = Path(briefings_root)

    def list_keys(self) -> list[str]:
        return sorted(path.stem for path in self._root.glob("*.md"))

    def get(self, key: str) -> str:
        path = self._root / f"{key}.md"
        if not path.exists():
            raise BriefingNotFoundError(key)
        return path.read_text()
