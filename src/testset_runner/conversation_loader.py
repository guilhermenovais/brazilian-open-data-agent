"""ConversationTestsetLoader: loads, validates, and content-hashes a scripted conversation
test set (008 contracts/conversation-testset.md "Loader rules"). Mirrors `loader.py`."""

import hashlib
import json
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from testset_runner.conversation_models import ConversationTestset, ScriptedConversation
from testset_runner.exceptions import TestsetLoadError

_CONVERSATIONS_ADAPTER = TypeAdapter(list[ScriptedConversation])


class ConversationTestsetLoader:
    def load(self, path: str | Path) -> ConversationTestset:
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
            conversations = _CONVERSATIONS_ADAPTER.validate_python(raw_records)
        except ValidationError as exc:
            raise TestsetLoadError(
                f"Testset file at {file_path} has one or more invalid records: {exc}"
            ) from exc

        seen_ids: set[str] = set()
        for conversation in conversations:
            if conversation.id in seen_ids:
                raise TestsetLoadError(
                    f"Testset file at {file_path} has a duplicate conversation id={conversation.id!r}"
                )
            seen_ids.add(conversation.id)
            for k, turn in enumerate(conversation.turns, start=1):
                if turn.scored is True and not turn.has_expectation:
                    raise TestsetLoadError(
                        f"Testset file at {file_path}: conversation {conversation.id!r} turn {k} "
                        "is scored but has neither 'expected' nor 'expected_outcome'"
                    )

        content_hash = hashlib.sha256(raw_bytes).hexdigest()
        return ConversationTestset(
            path=str(file_path), content_hash=content_hash, conversations=conversations
        )
