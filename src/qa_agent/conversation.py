"""Conversation turns and history trimming for the conversational path (008 data-model.md).

Only the visible text of a conversation is modelled here: the user's message and the
agent's final reply (FR-001). Tool calls, tool results and any other intermediate content
from earlier turns never cross into a later turn, so every fact a later answer states must
be retrieved again in that turn (FR-005).

Deliberately framework-free (no `pydantic_ai` import, Eng. Principle 1): converting turns
into model messages is a few lines in `capabilities.py`, the existing wiring point.
"""

from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    """One earlier, visible exchange in a chat."""

    question: str = Field(min_length=1)
    """The user's message text, stripped."""
    answer: str | None = None
    """The agent's final visible reply text. `None` when the turn has no reply (e.g. the
    request ended in an `ErrorChunk`). Never contains tool calls or results."""

    @property
    def size(self) -> int:
        """The characters this turn costs against the history limit."""
        return len(self.question) + len(self.answer or "")


class ConversationContext(BaseModel):
    """Everything `answer_turn` needs besides the current message."""

    conversation_id: str = Field(min_length=1)
    """The web UI chat `id`, or `"<run_id>:<conversation id>"` in the conversation runner."""
    turn_index: int = Field(ge=1)
    """Position of the current message in the conversation. It equals `len(history) + 1`
    before trimming, because trimming never renumbers."""
    history: list[ConversationTurn] = []
    """Oldest first. Full, untrimmed: trimming happens inside `answer_turn`."""


def fit_history(turns: list[ConversationTurn], char_limit: int) -> list[ConversationTurn]:
    """The longest contiguous most-recent suffix of `turns` whose total size fits `char_limit`.

    Walks from the newest turn backwards and stops at the **first** turn that does not fit,
    instead of skipping it and packing smaller, older turns into the space left. That keeps
    the kept context coherent: the model never sees turn 3 without turn 4 (research.md R3).
    A single newest turn larger than the whole limit therefore yields `[]`, and the current
    message is still answered (FR-011: never fail). Text is never truncated.
    """
    kept = 0
    used = 0
    for turn in reversed(turns):
        if used + turn.size > char_limit:
            break
        used += turn.size
        kept += 1
    return turns[len(turns) - kept :]
