"""CSV reader: every column read as raw strings, never auto-coerced to numeric types.

Numeric interpretation is deliberately deferred to numeric.py's per-value locale
detection (research.md §2) — the parser here must not destroy original formatting
like "1.234,56" by inferring a numeric dtype.
"""

from pathlib import Path

import pandas as pd


class CsvReader:
    def read(self, path: Path) -> pd.DataFrame:
        return pd.read_csv(
            path,
            dtype=str,
            keep_default_na=False,
            na_filter=False,
            engine="c",
        )
