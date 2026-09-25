"""Renders a versioned system prompt template with the selected briefing injected.

Prompts live at prompts/system_<version>.md, named/diffable/versioned (Eng. Principle 8)
and never edited in place. `v1` is frozen for the standalone `answer_question` path, so the
testset runner's model input never changes (008 FR-014, SC-007). `v2` exists for the
conversational `answer_turn` path: it keeps every v1 rule and adds the rules on how earlier
turns may and may not be used (008 research.md R4).
"""

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def render(briefing: str, version: str = "v1") -> str:
    """An unknown `version` raises `FileNotFoundError`: a programming error, never
    reachable from user input."""
    template = (_PROMPTS_DIR / f"system_{version}.md").read_text()
    return template.format(briefing=briefing)
