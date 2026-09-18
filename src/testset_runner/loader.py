"""TestsetLoader: loads, validates, and content-hashes a testset file (research.md §7)."""

import hashlib
import json
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from testset_runner.exceptions import TestsetLoadError
from testset_runner.models import Question, Testset

_QUESTIONS_ADAPTER = TypeAdapter(list[Question])


class TestsetLoader:
    def load(self, path: str | Path) -> Testset:
        file_path = Path(path)
        try:
            raw_bytes = file_path.read_bytes()
        except OSError as exc:
            raise TestsetLoadError(f"Could not read testset file at {file_path}: {exc}") from exc

        try:
            raw_records = json.loads(raw_bytes)
        except json.JSONDecodeError as exc:
            raise TestsetLoadError(f"Testset file at {file_path} is not valid JSON: {exc}") from exc

        try:
            questions = _QUESTIONS_ADAPTER.validate_python(raw_records)
        except ValidationError as exc:
            raise TestsetLoadError(
                f"Testset file at {file_path} has one or more invalid records: {exc}"
            ) from exc

        seen_n: set[int] = set()
        for question in questions:
            if question.n in seen_n:
                raise TestsetLoadError(
                    f"Testset file at {file_path} has a duplicate question n={question.n}"
                )
            seen_n.add(question.n)

        content_hash = hashlib.sha256(raw_bytes).hexdigest()
        return Testset(path=str(file_path), content_hash=content_hash, questions=questions)
