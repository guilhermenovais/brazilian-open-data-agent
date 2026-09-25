"""Forgiving text matching for `equals`/`contains` filters and value-suggestion ranking.

Plain Python (standard library + pydantic), no `pydantic_ai` or `qa_agent` import
(Constitution Engineering Principle 1). Rules, from specs/009-text-value-matching
(research.md R1–R4, contracts/text-matching.md, contracts/value-suggestions.md):

- **Normalization** (R1): NFKD → drop combining marks → `casefold()` → each run of
  non-word characters or `_` becomes one space → collapse and trim whitespace. It is a
  comparison form only; stored values are never altered in any output.
- **equals** (R2): the whole normalized values are equal. Stopwords are never skipped.
- **contains** (R2): every query word is a prefix of some word of the stored value, in
  any order. Query words are the normalized words of the filter value minus stopwords,
  or all of them when only stopwords remain. No query words matches every value.
- **Stopwords** (R3): a named, versioned list, `stopwords/<name>.txt`, selected by
  `TextMatchingConfig.stopwords`. A changed list is a new file, never an edit.
- **Ranking** (R4): `overlap` counts query words that start a word of the stored value
  or its acronym (first letter of each non-stopword word). Candidates with overlap ≥ 1
  are ordered by overlap desc, row count desc, value asc (code point).

Missing values (None, NaN, empty or whitespace-only) are the caller's concern: they are
never passed here, never match and are never candidates.
"""

import functools
import importlib.resources
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources.abc import Traversable

from pydantic import BaseModel, ConfigDict, Field, field_validator

_NON_WORD = re.compile(r"[\W_]+")
_STOPWORD_LIST_NAME = re.compile(r"[A-Za-z0-9_]+")


class TextMatchingConfig(BaseModel):
    """Typed settings for text matching, suggestions and value lists (research.md R6)."""

    model_config = ConfigDict(frozen=True)

    value_list_threshold: int = Field(
        default=30,
        ge=0,
        description="A field is listed when `distinct_count <= value_list_threshold`. `0` lists nothing.",
    )
    max_suggestions: int = Field(
        default=5, ge=1, description="Maximum candidates per zero-match condition."
    )
    stopwords: str = Field(
        default="pt_v1",
        description="Must name a file `data_access/stopwords/<name>.txt`. Validated on construction.",
    )

    @field_validator("stopwords")
    @classmethod
    def _stopword_list_exists(cls, name: str) -> str:
        if not _STOPWORD_LIST_NAME.fullmatch(name) or not _stopword_file(name).is_file():
            raise ValueError(f"unknown stopword list {name!r}: no data_access/stopwords/{name}.txt")
        return name


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(_NON_WORD.sub(" ", stripped.casefold()).split())


@functools.cache
def load_stopwords(name: str) -> frozenset[str]:
    """The normalized words of `stopwords/<name>.txt`, skipping blank and `#` lines."""
    words: set[str] = set()
    for line in _stopword_file(name).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        word = normalize(line)
        if word:
            words.add(word)
    return frozenset(words)


def _stopword_file(name: str) -> Traversable:
    return importlib.resources.files("data_access") / "stopwords" / f"{name}.txt"


@dataclass(frozen=True)
class MatchRules:
    """The matching rules a `PandasQueryEngine` and the ranking apply (data-model.md)."""

    stopwords: frozenset[str]

    @classmethod
    def from_config(cls, config: TextMatchingConfig) -> "MatchRules":
        return cls(stopwords=load_stopwords(config.stopwords))

    def words(self, text: str) -> list[str]:
        return normalize(text).split()

    def query_words(self, value: str) -> list[str]:
        """Words of `value` minus stopwords, or all of them if only stopwords remain."""
        all_words = self.words(value)
        content = [w for w in all_words if w not in self.stopwords]
        return content or all_words

    def acronym(self, text: str) -> str:
        """First letter of each non-stopword word, joined; `""` if there is none."""
        return "".join(w[0] for w in self.words(text) if w not in self.stopwords)

    def equals(self, stored: str, value: str) -> bool:
        return normalize(stored) == normalize(value)

    def contains(self, stored: str, value: str) -> bool:
        stored_words = self.words(stored)
        return all(_starts_any(q, stored_words) for q in self.query_words(value))

    def overlap(self, stored: str, value: str) -> int:
        return self._overlap(stored, self.query_words(value))

    def _overlap(self, stored: str, query_words: list[str]) -> int:
        tokens = self.words(stored)
        acronym = self.acronym(stored)
        if acronym:
            tokens.append(acronym)
        return sum(1 for q in query_words if _starts_any(q, tokens))


def rank_candidates(
    value_counts: Mapping[str, int], value: str, rules: MatchRules, limit: int
) -> list[tuple[str, int, int]]:
    """`(stored value, overlap, row_count)` for every value with overlap ≥ 1, ordered by
    overlap desc, row_count desc, value asc (code point), first `limit` of them.

    `value_counts` maps each distinct **non-missing** stored value to its row count.
    """
    query_words = rules.query_words(value)
    scored = [
        (stored, overlap, count)
        for stored, count in value_counts.items()
        if (overlap := rules._overlap(stored, query_words)) >= 1
    ]
    scored.sort(key=lambda c: (-c[1], -c[2], c[0]))
    return scored[:limit]


def _starts_any(prefix: str, words: list[str]) -> bool:
    return any(w.startswith(prefix) for w in words)
