"""The `Dataset` abstraction: the sole owner of the dataset's folder/identifier model.

Capabilities never see absolute/physical paths (FR-001b) — they only ever pass around
the relative-path-based identifiers this module derives. Internally, `Dataset` walks
the full folder tree (including subfolders), but the tree/nesting itself is invisible
to callers beyond what's encoded in each identifier's relative path.

Collision detection is deliberately case-insensitive (keyed by `casefold()`) even
though this runs on a case-sensitive filesystem in CI: two physical files that differ
only by case would silently merge into one identifier if this dataset were ever
deployed on a case-insensitive filesystem, so the ambiguity must be caught here,
independent of the host filesystem's own case sensitivity.
"""

from collections import defaultdict
from pathlib import Path
from typing import Literal

import pandas as pd

from data_access.exceptions import DataSourceNotFoundError, IdentifierCollisionError, UnreadableSourceError
from data_access.models import DataSourceInfo
from data_access.readers import CsvReader, JsonReader
from data_access.readers.base import DataSourceReader

_EXTENSION_FORMATS: dict[str, Literal["csv", "json"]] = {".csv": "csv", ".json": "json"}

_READERS: dict[str, DataSourceReader] = {
    "csv": CsvReader(),
    "json": JsonReader(),
}


class Dataset:
    def __init__(self, root_path: str | Path) -> None:
        self._root = Path(root_path)
        self._index_cache: dict[str, Path] | None = None

    @property
    def _index(self) -> dict[str, Path]:
        if self._index_cache is None:
            self._index_cache = self._build_index()
        return self._index_cache

    def _build_index(self) -> dict[str, Path]:
        candidates: dict[str, list[tuple[str, Path]]] = defaultdict(list)
        for path in sorted(self._root.rglob("*")):
            if not path.is_file():
                continue
            fmt = _EXTENSION_FORMATS.get(path.suffix.lower())
            if fmt is None:
                continue
            identifier = path.relative_to(self._root).as_posix()
            candidates[identifier.casefold()].append((identifier, path))

        index: dict[str, Path] = {}
        for entries in candidates.values():
            if len(entries) > 1:
                identifier = entries[0][0]
                physical_paths = [str(path) for _, path in entries]
                raise IdentifierCollisionError(identifier, physical_paths)
            (identifier, path) = entries[0]
            index[identifier] = path
        return index

    def _format_for(self, identifier: str) -> Literal["csv", "json"]:
        fmt = _EXTENSION_FORMATS.get(Path(identifier).suffix.lower())
        assert fmt is not None
        return fmt

    def list_sources(self) -> list[DataSourceInfo]:
        sources: list[DataSourceInfo] = []
        for identifier, path in sorted(self._index.items()):
            fmt = self._format_for(identifier)
            try:
                _READERS[fmt].read(path)
                readable = True
            except Exception:
                readable = False
            sources.append(DataSourceInfo(identifier=identifier, format=fmt, readable=readable))
        return sources

    def read(self, identifier: str) -> pd.DataFrame:
        if identifier not in self._index:
            raise DataSourceNotFoundError(identifier)
        path = self._index[identifier]
        fmt = self._format_for(identifier)
        try:
            return _READERS[fmt].read(path)
        except Exception as exc:
            raise UnreadableSourceError(identifier, str(exc)) from exc

    def resolve(self, identifier: str) -> Path:
        if identifier not in self._index:
            raise DataSourceNotFoundError(identifier)
        return self._index[identifier]
