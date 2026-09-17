"""JSON reader: top-level array of flat objects, key-union across records.

Nested objects/arrays are out of scope (research.md §8) — nothing in the spec's
requirements implies nested JSON structures.
"""

import json
from pathlib import Path

import pandas as pd


class JsonReader:
    def read(self, path: Path) -> pd.DataFrame:
        with path.open("r", encoding="utf-8") as fh:
            records = json.load(fh)

        if not isinstance(records, list):
            raise ValueError(
                f"Expected a top-level JSON array of objects, got {type(records).__name__}"
            )

        parsed: list[dict[str, str | None]] = []
        columns: list[str] = []
        for record in records:
            if not isinstance(record, dict):
                raise ValueError(
                    f"Expected a flat JSON object per record, got {type(record).__name__}"
                )
            row: dict[str, str | None] = {}
            for key, value in record.items():
                if key not in columns:
                    columns.append(key)
                row[key] = None if value is None else str(value)
            parsed.append(row)

        rows = [{col: row.get(col) for col in columns} for row in parsed]
        return pd.DataFrame(rows, dtype=object)
