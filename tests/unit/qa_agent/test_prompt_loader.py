"""Unit tests for prompt_loader: versioned prompt files, briefing injection, fingerprint."""

import hashlib
import re
from pathlib import Path

import pytest

from qa_agent import prompt_loader

_PROMPTS_DIR = Path(prompt_loader.__file__).parent / "prompts"
_SYSTEM_V1_SHA256 = "75070ec7e4cb3ccb05f0933e67f7872b63504e2f1e89f86a07b1a9ac1d38eb98"


def test_render_includes_briefing_text_verbatim() -> None:
    briefing = "Este é um resumo de teste de um dataset fictício."
    rendered = prompt_loader.render(briefing, version="v1")
    assert briefing in rendered


def test_render_includes_fixed_portuguese_instructions() -> None:
    rendered = prompt_loader.render("qualquer briefing", version="v1")
    assert "português" in rendered.lower()
    assert "nunca" in rendered.lower()


# --- 008 ------------------------------------------------------------------------------


def test_008_system_v1_sha256_is_pinned() -> None:
    """FR-005: system_v1.md is never edited; a new behavior needs a new versioned file."""
    digest = hashlib.sha256((_PROMPTS_DIR / "system_v1.md").read_bytes()).hexdigest()
    assert digest == _SYSTEM_V1_SHA256


def test_008_us1_v2_renders_briefing_verbatim() -> None:
    briefing = "Briefing de teste com acentuação: dotação, orçamento."
    assert briefing in prompt_loader.render(briefing, "v2")


def test_008_v2_has_single_briefing_placeholder() -> None:
    raw = (_PROMPTS_DIR / "system_v2.md").read_text()
    assert raw.count("{briefing}") == 1
    without_placeholder = raw.replace("{briefing}", "")
    assert "{" not in without_placeholder
    assert "}" not in without_placeholder


def test_008_us1_v2_mentions_needs_clarification_and_outcome_field() -> None:
    raw = (_PROMPTS_DIR / "system_v2.md").read_text()
    assert "needs_clarification" in raw
    assert "outcome" in raw


def _numbered_rules(text: str) -> dict[int, str]:
    """Each top-level numbered rule ("N. ...") with its indented continuation lines."""
    rules: dict[int, list[str]] = {}
    current: int | None = None
    for line in text.splitlines():
        head = line.split(".", 1)[0]
        if head.isdigit() and line.startswith(head + ". "):
            current = int(head)
            rules[current] = [line]
        elif current is not None and line.startswith("   "):
            rules[current].append(line)
        else:
            current = None
    return {n: "\n".join(lines) for n, lines in rules.items()}


def test_008_us2_v2_lists_all_four_outcome_values() -> None:
    raw = (_PROMPTS_DIR / "system_v2.md").read_text()
    for value in ("full", "partial", "none", "needs_clarification"):
        assert f'"{value}"' in raw


def test_008_us2_v2_carries_over_v1_rules_1_2_3_6_7() -> None:
    """FR-006: only rules 4, 5 and 8 change; the others are carried over word for word."""
    v1 = _numbered_rules((_PROMPTS_DIR / "system_v1.md").read_text())
    v2 = _numbered_rules((_PROMPTS_DIR / "system_v2.md").read_text())
    assert sorted(v2) == list(range(1, 9))
    for n in (1, 2, 3, 6, 7):
        assert v2[n] == v1[n]
    for n in (4, 5, 8):
        assert v2[n] != v1[n]


# --- 008 US4: version discovery, validation, fingerprint --------------------------------

from qa_agent.exceptions import UnknownPromptVersionError  # noqa: E402


def test_008_us4_available_versions() -> None:
    assert prompt_loader.available_versions() == ["v1", "v2", "v3"]


def test_008_us4_default_is_v2() -> None:
    assert prompt_loader.DEFAULT_PROMPT_VERSION == "v2"
    briefing = "b"
    assert prompt_loader.render(briefing) == prompt_loader.render(briefing, "v2")


def test_008_us4_3_check_version_rejects_unknown() -> None:
    with pytest.raises(UnknownPromptVersionError) as exc_info:
        prompt_loader.check_version("v9")
    exc = exc_info.value
    assert isinstance(exc, ValueError)
    assert exc.requested == "v9"
    assert exc.available == ["v1", "v2", "v3"]
    assert str(exc) == "unknown prompt version 'v9' (available: v1, v2, v3)"


def test_008_us4_3_render_rejects_unknown() -> None:
    with pytest.raises(UnknownPromptVersionError):
        prompt_loader.render("b", "v9")


def test_008_us4_render_v1_equals_v1_template() -> None:
    briefing = "Briefing de teste."
    template = (_PROMPTS_DIR / "system_v1.md").read_text()
    assert prompt_loader.render(briefing, "v1") == template.format(briefing=briefing)


def test_008_us4_6_fingerprint() -> None:
    text = "Descrição da dotação orçamentária."
    assert prompt_loader.fingerprint(text) == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert prompt_loader.fingerprint(text) == prompt_loader.fingerprint(str(text))
    assert prompt_loader.fingerprint(text) != prompt_loader.fingerprint(text + " ")
    assert prompt_loader.fingerprint("dotação") != prompt_loader.fingerprint("dotacao")


# --- 008-chat-conversation-history: system_v3 (conversational path) ----------------------


def _normalized_rules(text: str) -> dict[int, str]:
    """Each top-level numbered rule, whitespace-normalized, keyed by its number."""
    rules: dict[int, str] = {}
    for match in re.finditer(r"^(\d+)\. (.*?)(?=^\d+\. |^\S|\Z)", text, re.MULTILINE | re.DOTALL):
        rules[int(match.group(1))] = " ".join(match.group(2).split())
    return rules


def test_render_v3_includes_the_briefing() -> None:
    briefing = "Resumo fictício para o teste da versão 3."
    assert briefing in prompt_loader.render(briefing, "v3")


def test_v3_keeps_every_v1_rule_except_the_reworded_rule_2() -> None:
    v1_rules = _normalized_rules(prompt_loader.render("B", "v1"))
    v3_rules = _normalized_rules(prompt_loader.render("B", "v3"))

    assert set(v1_rules) == set(range(1, 9))
    for number, rule in v1_rules.items():
        if number == 2:
            continue
        assert v3_rules[number] == rule
    assert "durante este mesmo atendimento" in v1_rules[2]
    assert "nesta mesma resposta, durante o turno atual" in v3_rules[2]


def test_v3_has_a_conversation_section() -> None:
    rendered = prompt_loader.render("B", "v3")
    assert "\nConversa:\n" in rendered
    assert "consultados novamente" in rendered
    assert "não herda assunto" in rendered


def test_v3_has_the_clarification_rule() -> None:
    rendered = " ".join(prompt_loader.render("B", "v3").split())
    assert "pediu ao usuário que esclarecesse" in rendered
    assert "combine-a com a pergunta original" in rendered
    assert "peça novamente apenas o que falta" in rendered
