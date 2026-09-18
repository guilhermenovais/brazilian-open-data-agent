"""Renders the versioned system prompt template with the selected briefing injected.

The prompt itself lives at prompts/system_v1.md, named/diffable/versioned (Eng.
Principle 8) — never edited in place.
"""

from pathlib import Path

_TEMPLATE_PATH = Path(__file__).parent / "prompts" / "system_v1.md"


def render(briefing: str) -> str:
    template = _TEMPLATE_PATH.read_text()
    return template.format(briefing=briefing)
