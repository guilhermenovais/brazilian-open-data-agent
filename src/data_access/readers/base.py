"""Reader protocol: one implementation per data source format."""

from pathlib import Path
from typing import Protocol

import pandas as pd


class DataSourceReader(Protocol):
    def read(self, path: Path) -> pd.DataFrame: ...
