"""Builds data/testsets/conversations/orcamentos-aeb-csv-conversations.json (T036, T041, T046).

Every `expected` value is computed here by a deterministic pandas query over
`dados_gerais/tb_geral.csv`, never hand-read or taken from model output (Constitution
Principles I/VI). Re-run from the repository root to regenerate the file byte for byte:

    .venv/bin/python specs/008-chat-conversation-history/build_conversation_testset.py

Scoring convention (contracts/conversation-testset.md): only the turn a criterion measures
is scored; every context turn sets `"scored": false` (it may still document its expected
value). Note: in this dataset the AEB has rows only for 2000-2013 (no 2004/2006), and
2014-2019 rows belong to the MCTIC only, so follow-ups about the AEB use years it covers.
"""

import json
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = "dados_gerais/tb_geral.csv"
CSV = REPO_ROOT / "data" / "datasets" / "orcamentos-aeb-csv" / SOURCE
OUT = REPO_ROOT / "data" / "testsets" / "conversations" / "orcamentos-aeb-csv-conversations.json"

AEB = "Agência Espacial Brasileira"
MCTIC = "Ministério da Ciência, Tecnologia, Inovações e Comunicações"

df = pd.read_csv(CSV)


def total(metric: str, year: int, unit: str | None = None) -> str:
    rows = df[df.data_ano == year]
    if unit is not None:
        rows = rows[rows.nome_unidade == unit]
    return str(int(rows[metric].sum()))


def action_value(metric: str, year: int, action_contains: str) -> str:
    rows = df[(df.data_ano == year) & df.nome_acao.str.contains(action_contains, regex=False)]
    assert len(rows) == 1, (year, action_contains, len(rows))
    return str(int(rows[metric].iloc[0]))


def top_actions(unit: str, year: int, n: int) -> pd.DataFrame:
    rows = df[(df.data_ano == year) & (df.nome_unidade == unit)]
    return rows.nlargest(n, "pago")


def top_program_by_paid(unit: str, year: int) -> str:
    rows = df[(df.data_ano == year) & (df.nome_unidade == unit)]
    return str(rows.groupby("nome_programa")["pago"].sum().idxmax())


def program_total(metric: str, unit: str, year: int, program: str) -> str:
    rows = df[(df.data_ano == year) & (df.nome_unidade == unit) & (df.nome_programa == program)]
    return str(int(rows[metric].sum()))


def turn(message: str, expected: str | None = None, *, scored: bool | None = None,
         expected_outcome: str | None = None) -> dict:
    record: dict = {"message": message}
    if expected is not None:
        record["expected"] = expected
        record["source"] = SOURCE
    if expected_outcome is not None:
        record["expected_outcome"] = expected_outcome
    if scored is not None:
        record["scored"] = scored
    return record


def conversation(conv_id: str, category: str, description: str, turns: list[dict]) -> dict:
    return {"id": conv_id, "category": category, "description": description, "turns": turns}


top3_aeb_2012 = top_actions(AEB, 2012, 3)
min_committed_of_top3 = str(int(top3_aeb_2012["empenhado"].min()))
top_program_mctic_2018 = top_program_by_paid(MCTIC, 2018)

conversations = [
    # --- SC-001: follow-ups (last turn scored) -----------------------------------------
    conversation(
        "follow-up-year-01", "follow-up-year",
        "Muda só o ano. Esperado: soma de pago da AEB em 2011.",
        [
            turn("Quanto foi pago pela Agência Espacial Brasileira em 2010?", total("pago", 2010, AEB), scored=False),
            turn("e em 2011?", total("pago", 2011, AEB)),
        ],
    ),
    conversation(
        "follow-up-year-02", "follow-up-year",
        "Muda só o ano de uma pergunta sobre empenho. Esperado: soma de empenhado da AEB em 2009.",
        [
            turn("Qual foi o valor empenhado pela AEB em 2008?", total("empenhado", 2008, AEB), scored=False),
            turn("e em 2009?", total("empenhado", 2009, AEB)),
        ],
    ),
    conversation(
        "follow-up-year-03", "follow-up-year",
        "Total geral (todas as unidades), muda só o ano. Esperado: soma de pago em 2017.",
        [
            turn("Quanto foi pago no total em 2016?", total("pago", 2016), scored=False),
            turn("e em 2017?", total("pago", 2017)),
        ],
    ),
    conversation(
        "follow-up-metric-01", "follow-up-metric",
        "Mantém AEB e 2012, troca pago por empenhado. Esperado: soma de empenhado da AEB em 2012.",
        [
            turn("Quanto foi pago pela AEB em 2012?", total("pago", 2012, AEB), scored=False),
            turn("e quanto foi empenhado?", total("empenhado", 2012, AEB)),
        ],
    ),
    conversation(
        "follow-up-metric-02", "follow-up-metric",
        "Mantém AEB e 2003, troca dotação por pago. Esperado: soma de pago da AEB em 2003.",
        [
            turn("Qual foi a dotação atual total da AEB em 2003?", total("dotacao_atual", 2003, AEB), scored=False),
            turn("e o valor pago?", total("pago", 2003, AEB)),
        ],
    ),
    conversation(
        "follow-up-metric-03", "follow-up-metric",
        "Mantém a ação Amazônia-1 em 2010, troca pago por dotação atual. Esperado: dotacao_atual dessa linha.",
        [
            turn("Quanto foi pago pelo desenvolvimento do satélite Amazônia-1 em 2010?",
                 action_value("pago", 2010, "Amazônia-1"), scored=False),
            turn("e qual foi a dotação atual?", action_value("dotacao_atual", 2010, "Amazônia-1")),
        ],
    ),
    conversation(
        "follow-up-reference-01", "follow-up-reference",
        "\"dessas\" = as 3 ações da AEB com maior pago em 2012. Esperado: menor empenhado entre elas.",
        [
            turn("Quais foram as 3 ações da AEB com maior valor pago em 2012?", scored=False),
            turn("Qual dessas teve o menor valor empenhado, e quanto foi?", min_committed_of_top3),
        ],
    ),
    conversation(
        "follow-up-reference-02", "follow-up-reference",
        "\"nessa mesma ação\" = CBERS-3. Esperado: pago da ação CBERS-3 em 2010.",
        [
            turn("Quanto foi pago pelo desenvolvimento do satélite sino-brasileiro CBERS-3 em 2008?",
                 action_value("pago", 2008, "CBERS-3"), scored=False),
            turn("E quanto foi pago nessa mesma ação em 2010?", action_value("pago", 2010, "CBERS-3")),
        ],
    ),
    conversation(
        "follow-up-reference-03", "follow-up-reference",
        f"\"esse programa\" = programa do MCTIC com maior pago em 2018 ({top_program_mctic_2018}). "
        "Esperado: soma de empenhado desse programa no MCTIC em 2018.",
        [
            turn("Qual programa do Ministério da Ciência, Tecnologia, Inovações e Comunicações teve o maior valor pago em 2018?",
                 scored=False),
            turn("Quanto foi empenhado nesse programa nesse mesmo ano?",
                 program_total("empenhado", MCTIC, 2018, top_program_mctic_2018)),
        ],
    ),
    # --- SC-004: a complete question after an unrelated one (standalone turn scored) -----
    conversation(
        "standalone-after-unrelated-01", "standalone-after-unrelated",
        "A segunda pergunta é completa e não herda a AEB. Esperado: soma de empenhado (todas as unidades) em 2016.",
        [
            turn("Quanto foi pago pela AEB em 2010?", total("pago", 2010, AEB), scored=False),
            turn("Qual foi o valor empenhado total em 2016?", total("empenhado", 2016)),
        ],
    ),
    conversation(
        "standalone-after-unrelated-02", "standalone-after-unrelated",
        "A segunda pergunta é completa e não herda AEB nem 2012 nem o recorte de 3 ações. Esperado: soma de pago em 2019.",
        [
            turn("Quais foram as 3 ações da AEB com maior valor pago em 2012?", scored=False),
            turn("Quanto foi pago no total em 2019?", total("pago", 2019)),
        ],
    ),
    # --- SC-002 / US2: clarification --------------------------------------------------
    conversation(
        "clarification-01", "clarification",
        "Pergunta vaga, depois a resposta completa. Esperado: soma de pago da AEB em 2011.",
        [
            turn("Me fale sobre o orçamento.", scored=False, expected_outcome="none"),
            turn("o valor pago pela Agência Espacial Brasileira em 2011", total("pago", 2011, AEB)),
        ],
    ),
    conversation(
        "clarification-02", "clarification",
        "Pergunta vaga sobre a AEB, depois a métrica e o ano. Esperado: soma de empenhado da AEB em 2013.",
        [
            turn("Quero saber sobre os gastos da AEB.", scored=False),
            turn("o total empenhado em 2013", total("empenhado", 2013, AEB)),
        ],
    ),
    conversation(
        "clarification-03", "clarification",
        "\"valor do orçamento\" é ambíguo (dotação/empenhado/liquidado/pago; 004 testset n=10). "
        "A resposta escolhe a métrica. Esperado: soma de pago da AEB em 2005.",
        [
            turn("Qual foi o valor do orçamento da Agência Espacial Brasileira em 2005?", scored=False),
            turn("o valor pago", total("pago", 2005, AEB)),
        ],
    ),
    conversation(
        "clarification-insufficient-01", "clarification-insufficient",
        "A resposta ao pedido de esclarecimento ainda não diz qual satélite, nem o ano, nem a métrica "
        "(há várias ações de satélite). Esperado: pedir de novo o que falta (outcome none).",
        [
            turn("Quero saber quanto foi gasto em uma ação.", scored=False),
            turn("aquela do satélite", expected_outcome="none"),
        ],
    ),
    conversation(
        "clarification-ignored-01", "clarification-ignored",
        "Depois da pergunta vaga, o usuário faz outra pergunta completa. Esperado: soma de pago em 2014.",
        [
            turn("Me fale sobre o orçamento.", scored=False),
            turn("Quanto foi pago no total em 2014?", total("pago", 2014)),
        ],
    ),
    # --- SC-005: a follow-up-style first message in a fresh chat ------------------------
    conversation(
        "fresh-chat-follow-up-01", "fresh-chat-follow-up",
        "Sem conversa anterior, \"e em 2016?\" não tem assunto: deve ser recusada como vaga.",
        [turn("e em 2016?", expected_outcome="none")],
    ),
    conversation(
        "fresh-chat-follow-up-02", "fresh-chat-follow-up",
        "Sem conversa anterior, \"e o empenhado?\" não tem unidade nem ano: deve ser recusada como vaga.",
        [turn("e o empenhado?", expected_outcome="none")],
    ),
]

# --- SC-006: one long conversation (>= 20 turns), all context-only -------------------
long_turns: list[dict] = []
for year in (2000, 2001, 2002, 2003, 2005, 2007, 2008, 2009, 2010, 2011):
    long_turns.append(turn(f"Quanto foi pago pela AEB em {year}?", total("pago", year, AEB), scored=False))
    long_turns.append(turn("e quanto foi empenhado?", total("empenhado", year, AEB), scored=False))
for year in (2014, 2015):
    long_turns.append(turn(f"Quanto foi pago no total em {year}?", total("pago", year), scored=False))
conversations.append(
    conversation(
        "long-conversation-01", "long-conversation",
        f"{len(long_turns)} turnos alternando pago/empenhado por ano. Nenhum turno é pontuado: mede que "
        "nenhum turno falha (errored) e que, no limite padrão, history_turns_used == history_turns_sent.",
        long_turns,
    )
)

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(conversations, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {len(conversations)} conversations to {OUT.relative_to(REPO_ROOT)}")
