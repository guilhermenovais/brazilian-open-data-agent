"""Unit tests for prompt_loader.render (briefing injection into system_v1.md)."""

import hashlib
import re
from pathlib import Path

import pytest

from qa_agent import prompt_loader


def test_render_includes_briefing_text_verbatim() -> None:
    briefing = "Este é um resumo de teste de um dataset fictício."
    rendered = prompt_loader.render(briefing)
    assert briefing in rendered


def test_render_includes_fixed_portuguese_instructions() -> None:
    rendered = prompt_loader.render("qualquer briefing")
    assert "português" in rendered.lower()
    assert "nunca" in rendered.lower()


def test_render_defaults_to_v1() -> None:
    briefing = "qualquer briefing"
    assert prompt_loader.render(briefing) == prompt_loader.render(briefing, version="v1")


def test_render_of_an_unknown_version_raises() -> None:
    with pytest.raises(FileNotFoundError):
        prompt_loader.render("qualquer briefing", version="nope")


# --- 008: system_v2 (conversational path) ------------------------------------------

_PROMPTS_DIR = Path(prompt_loader.__file__).parent / "prompts"
# system_v1.md is frozen (Eng. Principle 8, 008 FR-014/SC-007): the standalone path's model
# input must never change. Update this only together with a deliberate new prompt version.
_SYSTEM_V1_SHA256 = "75070ec7e4cb3ccb05f0933e67f7872b63504e2f1e89f86a07b1a9ac1d38eb98"


def _numbered_rules(text: str) -> dict[int, str]:
    """Each top-level numbered rule, whitespace-normalized, keyed by its number."""
    rules: dict[int, str] = {}
    for match in re.finditer(r"^(\d+)\. (.*?)(?=^\d+\. |^\S|\Z)", text, re.MULTILINE | re.DOTALL):
        rules[int(match.group(1))] = " ".join(match.group(2).split())
    return rules


def test_system_v1_is_unchanged() -> None:
    raw = (_PROMPTS_DIR / "system_v1.md").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == _SYSTEM_V1_SHA256


def test_render_v2_includes_the_briefing() -> None:
    briefing = "Resumo fictício para o teste da versão 2."
    assert briefing in prompt_loader.render(briefing, version="v2")


def test_v2_keeps_every_v1_rule_except_the_reworded_rule_2() -> None:
    v1_rules = _numbered_rules(prompt_loader.render("B"))
    v2_rules = _numbered_rules(prompt_loader.render("B", version="v2"))

    assert set(v1_rules) == set(range(1, 9))
    for number, rule in v1_rules.items():
        if number == 2:
            continue
        assert v2_rules[number] == rule
    assert "durante este mesmo atendimento" in v1_rules[2]
    assert "nesta mesma resposta, durante o turno atual" in v2_rules[2]


def test_v2_has_a_conversation_section() -> None:
    rendered = prompt_loader.render("B", version="v2")
    assert "\nConversa:\n" in rendered
    assert "consultados novamente" in rendered
    assert "não herda assunto" in rendered


def test_v2_has_the_clarification_rule() -> None:
    rendered = " ".join(prompt_loader.render("B", version="v2").split())
    assert "pediu ao usuário que esclarecesse" in rendered
    assert "combine-a com a pergunta original" in rendered
    assert "peça novamente apenas o que falta" in rendered
