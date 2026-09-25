# Contract: Outcome-Aware Grading

**Covers**: FR-012–FR-020 · US3 · research §6, §7 · supersedes nothing (it extends
`004 contracts/running.md` grading)

## `testset_runner.matcher`

```python
def contains_amount(text: str) -> bool: ...

class DeterministicMatcher:
    def __init__(self, strategy: MatchStrategy | None = None) -> None: ...
    def grade(
        self,
        expected: str,
        actual_answer: str,
        *,
        expected_outcome: Outcome | None = None,
        agent_outcome: Outcome | None = None,
    ) -> Literal["matched", "not_matched", "needs_review"]: ...
```

`MatchStrategy` / `NumericMatchStrategy` are **unchanged**.

### `grade` rules (checked in order)

| # | Condition | Returns |
|---|---|---|
| 1 | `expected_outcome is None` | `strategy.evaluate(expected, actual_answer)` |
| 2 | `agent_outcome != expected_outcome` | `"not_matched"` |
| 3 | `expected_outcome in ("none", "needs_clarification")` | `"not_matched"` if `contains_amount(actual_answer)` else `"matched"` |
| 4 | otherwise (`full` / `partial`) | `strategy.evaluate(expected, actual_answer)` |

`expected` is ignored in rule 3. Rule 2 applies even when `agent_outcome is None` and an
expected outcome is set: `None != "none"` gives `not_matched`.

### `contains_amount` rules

The function returns `True` if and only if the text contains at least one of the following:

| Pattern | Text that matches | Text that doesn't match |
|---|---|---|
| `R\$\s*-?\d` | `R$ 42`, `R$42.750,00`, `R$ -5` | `R$` alone |
| `\d[.,]\d` | `1.234`, `12,5`, `206.805.295`, `0,36` | `2005.`, `2005, 2006`, `1. Valor pago` |
| `\d\s*%` | `36%`, `12,5 %` | `por cento` written in words |

The following must **not** match: `2005`, `2008 a 2012`, `Amazônia-1`, `CBERS-3`, `2)` and
`1.` at the start of a line.

## `testset_runner.models.Question`

`expected_outcome: Outcome | None = None`. The loader rejects an invalid value (e.g.
`"maybe"`) with `TestsetLoadError`, and the message includes pydantic's location for the
offending record.

## `run_testset` changes

For each question:

```text
if answer_result.errored:          match_status = "errored"          # FR-017, unchanged
else: match_status = grader.grade(question.expected, answer_result.answer,
                                  expected_outcome=question.expected_outcome,
                                  agent_outcome=answer_result.outcome)
QuestionResult(..., expected_outcome=question.expected_outcome)     # FR-018
```

## Test obligations (named `test_008_us3_<M>_...`, one per acceptance scenario)

| Scenario | Arrange | Assert |
|---|---|---|
| US3-1 | expected `none`, outcome `none`, answer "Não há dados para 2020 sobre o Amazônia-1." | `matched` |
| US3-2 | expected `none`, outcome `partial` | `not_matched` |
| US3-3 | expected `needs_clarification`, same outcome, answer contains "R$ 206.805.295" | `not_matched` |
| US3-4 | expected `full`, `expected="65000"`, outcome `full` with "65.000" → `matched`; outcome `partial` with "65.000" → `not_matched` | as stated |
| US3-5 | no expected outcome, each existing matcher unit case | same status as before |
| US3-6 | expected `none`, `errored=True` answerer | `errored` |
| US3-7 | load the bundled testset | #48/#50 = `none`, #49 = `needs_clarification`, the other 47 = `None` |
| Edge | expected `full`, non-numeric `expected`, outcome matches → `needs_review`; outcome differs → `not_matched` | as stated |
| Edge | invalid `expected_outcome` in a fixture file | `TestsetLoadError` |
| SC-007 | every result in the committed run fixtures regraded with `expected_outcome=None` | stored `match_status` |

All grading tests run without `pydantic-ai` or a model (FR-020).
