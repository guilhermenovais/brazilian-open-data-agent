# Contract: System Prompt v2 and Briefing Wording Guidance

**Covers**: FR-005, FR-006, FR-007 · research §8, §9

## Files

| File | Rule |
|---|---|
| `src/qa_agent/prompts/system_v1.md` | Must not be modified. Its SHA-256 is pinned by a unit test written before any other change. |
| `src/qa_agent/prompts/system_v2.md` | New. Portuguese. Contains exactly one `{briefing}` placeholder and no other `{`/`}` (so `str.format` works). |

## Required v2 rules

Each item is a behavior the prompt must instruct. The wording is chosen at implementation
time. Items marked **(v1)** are carried over word for word from `system_v1.md`.

| # | Rule | Source |
|---|---|---|
| 1 | Always answer in Portuguese. **(v1)** | v1 rule 1 |
| 2 | Never state a number, name or fact that wasn't obtained by a query in this same session. **(v1)** | v1 rule 2 |
| 3 | Use the tools and chain as many calls as needed within the step limit. **(v1)** | v1 rule 3 |
| 4 | **Ambiguity.** If the question could refer to more than one measure (as the dataset description explains) and the readings give different amounts, don't choose. Answer with a clarifying question in Portuguese that lists the possible readings in plain language (e.g. "valor autorizado", "valor empenhado", "valor liquidado", "valor pago") and contains no values from the dataset. Report `needs_clarification`. If the question's wording already names the measure, according to the dataset description, answer with that measure without asking. If every reading gives the same amount, answer directly and say that the readings agree. | FR-006 a–b; #49 |
| 5 | **Coverage.** If the data doesn't cover the question, say so plainly and invent nothing (v1). **Never give the value, or the name, of a similar or related item as a substitute.** If nothing in the data matches what was asked, report `none`. If the question is not covered at all (e.g. a period outside the data), report `none`, even if it is also ambiguous. If only part is covered, answer that part, declare what is missing, and report `partial`. | FR-006 c; #48, #50; spec Edge Cases |
| 6 | Never repeat technical error text. Translate failures into plain language. **(v1)** | v1 rule 6 |
| 7 | Never mention file names, column names or internal identifiers. **(v1)** | v1 rule 7 |
| 8 | **Outcome field.** Report the classification **only** in the `outcome` field of the structured answer. Never write it, or any "Classificação:" line, in the answer text. Values: `full`, `partial`, `none`, `needs_clarification`, each with a one-line definition. | FR-006 d; #50 |

Rule 7's "no column names" also applies to rule 4: readings are described in plain language
(US1 AC1).

## Briefing section (`data/briefings/orcamentos-aeb-csv.md`)

The new section is titled **"Qual medida a pergunta pede"** and goes after the field
dictionary. It must state:

1. **Wording that names a measure**:

   | Wording | Measure |
   |---|---|
   | "gasto", "gastou", "pago", "pagamento", "desembolso" | paid (`pago`) |
   | "orçamento previsto", "dotação", "autorizado" | authorized (`dotacao_atual`) |
   | "empenhado", "empenho" | committed (`empenhado`) |
   | "liquidado", "liquidação" | liquidated (`liquidado`) |

2. **Ambiguous wording**: "orçamento", "valor do orçamento" or "recursos" with no qualifier,
   when an amount is asked for. The four measures can differ a lot for the same scope (for
   the AEB in 2005: authorized ≈ 206.8 mi, paid ≈ 132.0 mi). The section doesn't say what
   the agent should do about this. That is the prompt's job.
3. **Counting questions**: "quantas ações tiveram execução/gastos em ANO" counts the
   records for that year, whatever the measure values (records with `pago = 0` included).
   This is not a choice of measure.

The existing synonyms table must not contradict item 1. Bare "gasto" is removed from the
committed (`empenhado`) row's synonyms if present unqualified. "Gasto empenhado" stays,
because it names the measure.

## Verification

- Unit: `system_v1.md` SHA-256 is unchanged. `render(b, "v2")` contains `b` verbatim.
  `render(b, "v1")` equals the v1 template formatted with `b`. v2 contains the strings
  `needs_clarification` and `outcome`.
- Live (quickstart §3): SC-001, SC-003 and SC-005.
