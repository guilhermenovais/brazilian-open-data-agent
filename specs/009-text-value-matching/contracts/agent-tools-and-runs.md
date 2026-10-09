# Contract: Agent Tool Descriptions, Settings and Run Records

Covers FR-016, FR-018 and FR-019 at the `qa_agent` and `testset_runner` boundaries.
Rationale: [research.md](../research.md) R6–R8.

## Tool wrappers (`qa_agent/tools.py`)

Signatures are unchanged. Each of `inspect_schema`, `query_rows` and `aggregate_rows`
passes `text_matching=ctx.deps.text_matching` to its capability. Budget and error handling
are unchanged.

### Descriptions the model sees (FR-018)

Asserted by `tests/unit/qa_agent/test_tools_description.py` via the captured
`ToolDefinition`s. Exact wording is free, but the stated facts are not:

| Tool / schema | Must state |
|---|---|
| `query_rows` description | text filters ignore case, accents and punctuation; `equals` compares the whole value; `contains` needs every word (filler words like "de"/"do" skipped) to start a word of the value, in any order; a result with 0 rows may include `value_suggestions` with real stored values to retry with |
| `aggregate_rows` description | same filter sentence and suggestion sentence (keeping every 007 fact asserted today) |
| `inspect_schema` description | each field reports `distinct_count`; `values` lists every stored value when there are at most `value_list_threshold`, and those exact values can be used in filters |
| `EqualsCondition.value` / `ContainsCondition.value` schema description | the short form of the matching rule |

`qa_agent/prompts/system_v1.md` and `system_v2.md`: **byte-identical** to before. No new
prompt version is added. `test_prompt_loader.py` / `test_standalone_unchanged.py` keep
passing unchanged.

## Settings and deps

```text
AgentSettings.text_matching: TextMatchingConfig = TextMatchingConfig()
AgentDeps.text_matching:     TextMatchingConfig = TextMatchingConfig()   # dataclass default_factory
QaAgentQuestionAnswerer(..., text_matching: TextMatchingConfig = TextMatchingConfig())
QaAgentQuestionAnswerer.text_matching -> TextMatchingConfig               # read-only property
```

`_answer_with_selection` builds `AgentDeps(..., text_matching=settings.text_matching)`.

## Run records (FR-016)

| Model | Field | Meaning |
|---|---|---|
| `TestRun` | `text_matching: TextMatchingConfig \| None = None` | Value used by the run. `None` = pre-009 run (not recorded). |
| `ConversationRun` | `text_matching: TextMatchingConfig \| None = None` | Same. |

`run_testset(..., text_matching=...)` and `run_conversations(..., text_matching=...)`
accept it (default `None`, so existing callers and tests are unaffected). The CLI passes
`answerer.text_matching`, the same object the answerer uses. Old run files still load, and
`compare` does not treat a difference in `text_matching` as incompatible.

### CLI report (both `run` and `run-conversations`)

One added line after the retry policy line:

```text
Text matching: value_list_threshold=30, max_suggestions=5, stopwords=pt_v1
```

(`not recorded` when the field is `None`, the same convention as the retry policy.) No new
flag or environment variable.
