"""Renders a versioned system prompt template with the selected briefing injected.

Each prompt version is a named file, `prompts/system_<version>.md` (e.g. `system_v1.md`,
`system_v2.md`), diffable and versioned (Eng. Principle 8) — never edited in place: a
behavior change is a new file. Versions are discovered from the files themselves, so
adding `system_v3.md` needs no code change.

`fingerprint` identifies a briefing's content: each answer carries the SHA-256 of the
briefing it used, so a run can always be tied to the exact briefing text, even though the
briefing file is edited in place (008 research §3, §5).
"""

import hashlib
import re
from pathlib import Path

from qa_agent.exceptions import UnknownPromptVersionError

DEFAULT_PROMPT_VERSION: str = "v2"

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_VERSION_FILE = re.compile(r"system_(v(\d+))\.md")


def available_versions() -> list[str]:
    """The version names found in `prompts/`, ordered by number (`v2` before `v10`)."""
    found: list[tuple[int, str]] = []
    for path in _PROMPTS_DIR.iterdir():
        match = _VERSION_FILE.fullmatch(path.name)
        if match is not None:
            found.append((int(match.group(2)), match.group(1)))
    return [name for _, name in sorted(found)]


def check_version(version: str) -> None:
    """Raises `UnknownPromptVersionError` if there is no prompt file for `version`."""
    available = available_versions()
    if version not in available:
        raise UnknownPromptVersionError(version, available)


def render(briefing: str, version: str = DEFAULT_PROMPT_VERSION) -> str:
    check_version(version)
    template = (_PROMPTS_DIR / f"system_{version}.md").read_text()
    return template.format(briefing=briefing)


def fingerprint(text: str) -> str:
    """SHA-256 hex digest of `text`'s UTF-8 bytes."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
