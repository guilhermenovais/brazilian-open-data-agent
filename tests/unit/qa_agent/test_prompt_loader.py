"""Unit tests for prompt_loader.render (briefing injection into system_v1.md)."""

from qa_agent import prompt_loader


def test_render_includes_briefing_text_verbatim() -> None:
    briefing = "Este é um resumo de teste de um dataset fictício."
    rendered = prompt_loader.render(briefing)
    assert briefing in rendered


def test_render_includes_fixed_portuguese_instructions() -> None:
    rendered = prompt_loader.render("qualquer briefing")
    assert "português" in rendered.lower()
    assert "nunca" in rendered.lower()
