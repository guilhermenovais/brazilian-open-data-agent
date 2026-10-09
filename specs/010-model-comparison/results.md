# Results: Local Model Comparison on the 50-Question Testset (010)

Live evaluation, 2026-10-09, code at `a5ae334`.

- **Testset**: `data/testsets/orcamentos-aeb-csv.json` (50 questions, content hash `fa66647e…`)
- **Agent**: unchanged. Prompt `v2`, retry policy `max_attempts=3, waits 2.0s x2.0 (cap 60.0s)`,
  text matching `value_list_threshold=30, max_suggestions=5, stopwords=pt_v1`, same briefing
  fingerprint `4f2597d6…` on every run.
- **Server**: local vLLM 0.29.0 on an RTX 5070 (12 GB, WSL2), one model at a time. Serve
  scripts are outside this repo, in `~/llm/run_*.sh`
  (https://github.com/guilhermenovais/open-model-scripts). Every run goes through `~/llm/bench_model.sh`,
  which adds the same server settings for every model (see "Round 2" below).
- **Sampling**: each model's `generation_config.json` defaults (the agent sets no temperature).
  vLLM's default `seed=0` makes generation **deterministic**: rerunning a configuration gives the
  same answers. Both Qwen3 configurations gave word-for-word identical answers in rounds 1 and 2.

Every number below comes from the run files listed here, through
`specs/010-model-comparison/compare_models.py`. Copies of all run files, every model's answer
to every question (`evidence/answers-round{1,2}.md`) and the logs are in
[`evidence/`](evidence/README.md). `evidence/regenerate.sh` rebuilds the tables from them.

## Setup per model

| Label | Checkpoint | Weights | Context | Tool format (vLLM) |
|---|---|---|---|---|
| qwen3-8b-think | `Qwen/Qwen3-8B-AWQ` | AWQ int4 | 40960 | `hermes`, `--reasoning-parser qwen3` (thinking on) |
| qwen3-8b-nothink | `Qwen/Qwen3-8B-AWQ` | AWQ int4 | 40960 | same, with `--default-chat-template-kwargs '{"enable_thinking": false}'` |
| llama-3.1-8b | `hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4` | AWQ int4 | 40960 | `llama3_json` + vLLM's `tool_chat_template_llama3.1_json.jinja` (local copy) |
| granite-3.1-8b | `RedHatAI/granite-3.1-8b-instruct-quantized.w4a16` | GPTQ-style W4A16 | 40960 | `granite`, built-in template |
| ministral-8b | `warshanks/Ministral-8B-Instruct-2410-AWQ` | AWQ W4A16 | 32768 (checkpoint max) | `mistral_defs_fix` (see below), HF tokenizer |
| xlam-2-8b | `Salesforce/Llama-xLAM-2-8b-fc-r`, quantized locally (`~/llm/quantize_xlam_w4a16.py`) | RTN W4A16 | 40960 | `xlam`, built-in template |
| phi-4-mini | `microsoft/Phi-4-mini-instruct` | online FP8 | 40960 | `phi4_mini_json` + vLLM's `tool_chat_template_phi4_mini.jinja` |
| gemma-3-4b | `unsloth/gemma-3-4b-it` (ungated mirror of `google/gemma-3-4b-it`) | online FP8 | 40960 | `pythonic` + vLLM's `tool_chat_template_gemma3_pythonic.jinja` |

All runs use `--kv-cache-dtype fp8 --attention-backend TRITON_ATTN --max-num-batched-tokens 4096`
(see `~/llm/run_qwen3_8b.sh` for why).

Choices that differ from the plan, and why:

- **Phi-4-mini and Gemma 3 4B run with FP8 weights, not bf16.** In bf16, Phi-4-mini's weights
  took 7.17 GiB and left 0.31 GiB of KV cache (about 5k tokens). The agent's prompts need 10k or
  more.
- **xLAM is a local round-to-nearest W4A16 quant.** vLLM 0.29 dropped bitsandbytes, and the only
  int4 checkpoint on the Hub is AMD Quark format. RTN without calibration is slightly lossier than
  the GPTQ/AWQ quants of the other 8B models.
- **Ministral needed two workarounds.** For `tool_choice="required"`, vLLM's Mistral parser nests
  each tool's schema under `anyOf` but leaves its `$defs` nested too. The `#/$defs/...` pointers
  then fail, and every request was rejected with "Grammar error: Pointer '/$defs/EqualsCondition'
  does not exist". `~/llm/mistral_defs_fix_tool_parser.py` is a parser plugin that moves the
  `$defs` to the root. The tokenizer is the HF one (`~/llm/models/ministral-8b-hf-tokenizer`), and
  its token ids were checked to match `tekken.json`.

### What the agent sends: `tool_choice="required"`

The agent's output type is a structured `AgentAnswer` (sent as the `final_result` tool), and plain
text output is not allowed. So pydantic-ai sends `tool_choice="required"` on **every** request.
vLLM enforces that with guided JSON decoding (xgrammar), which forces
`[{"name": ..., "parameters": ...}]`. Each model's native tool-call format and parser are then not
used (except Mistral's). The smoke test in `bench_model.sh` uses `tool_choice="auto"`, so it only
checks that the native format works. It does not predict agent behavior.

## Round 2: final comparison (uniform server settings)

`bench_model.sh` adds two settings to every model's server:

- `--structured-outputs-config '{"backend": "xgrammar", "disable_any_whitespace": true}'`
- `--override-generation-config '{"max_new_tokens": 8192}'`

| Label | Run id | Wall time |
|---|---|---|
| qwen3-8b-nothink | `20261009T120950189471Z` | 6 min |
| qwen3-8b-think | `20261009T130608039025Z` | 14 min |
| ministral-8b | `20261009T123506627415Z` | 5.5 min |
| llama-3.1-8b | `20261009T125159578786Z` | 10 min |
| phi-4-mini | `20261009T121744272116Z` | 5 min |
| gemma-3-4b | `20261009T124147889923Z` | 6.5 min |
| granite-3.1-8b | `20261009T121224424240Z` | 2.5 min |
| xlam-2-8b | `20261009T122923158060Z` | 11 min |

Wall time includes server startup (about 1 min).

**Official** is the runner's own score. **Text check** is this script's provisional check of the
13 text-valued questions (Q32–34, Q38–47). The runner always grades these `needs_review` (see the
`compare_models.py` docstring for the rule). **Combined** = official + text check. Per-category
columns use the combined count.

| Model | Official | matched / not / review / err | Text check | Combined | single-lookup | calculation | multiple-files | edge-cases | Errors by type | Steps/q |
|---|---|---|---|---|---|---|---|---|---|---|
| **qwen3-8b-nothink** | 30/50 (60%) | 30 / 7 / 13 / 0 | 12/13 | **42/50 (84%)** | 19/21 | 13/17 | 9/9 | 1/3 | – | 5.6 |
| **qwen3-8b-think** | 25/50 (50%) | 25 / 10 / 13 / 2 | 10/13 | **35/50 (70%)** | 12/21 | 15/17 | 7/9 | 1/3 | UnexpectedModelBehavior 1, ValidationError 1 | 2.2 |
| **ministral-8b** | 5/50 (10%) | 5 / 32 / 13 / 0 | 2/13 | **7/50 (14%)** | 2/21 | 2/17 | 2/9 | 1/3 | – | 7.1 |
| **llama-3.1-8b** | 3/50 (6%) | 3 / 30 / 12 / 5 | 1/12 | **4/50 (8%)** | 1/21 | 1/17 | 1/9 | 1/3 | BadRequestError 5 | 4.1 |
| **phi-4-mini** | 3/50 (6%) | 3 / 31 / 13 / 3 | 1/13 | **4/50 (8%)** | 1/21 | 0/17 | 1/9 | 2/3 | ValidationError 3 | 4.1 |
| **gemma-3-4b** | 2/50 (4%) | 2 / 24 / 10 / 14 | 2/10 | **4/50 (8%)** | 1/21 | 0/17 | 2/9 | 1/3 | BadRequestError 13, UsageLimitExceeded 1 | 4.3 |
| **granite-3.1-8b** | 2/50 (4%) | 2 / 35 / 13 / 0 | 1/13 | **3/50 (6%)** | 0/21 | 0/17 | 1/9 | 2/3 | – | 1.5 |
| **xlam-2-8b** | 2/50 (4%) | 2 / 27 / 8 / 13 | 1/8 | **3/50 (6%)** | 2/21 | 0/17 | 1/9 | 0/3 | UnexpectedModelBehavior 2, UsageLimitExceeded 5, ValidationError 6 | 3.2 |

**Summary**: Qwen3-8B is the only usable model of the seven with this agent. With thinking
**off**, it is both better (84% vs 70% combined, 60% vs 50% official) and over 2× faster than with
thinking on. Thinking on wins only on calculation (15/17 vs 13/17). All other models are at
6–14% combined. Much of that comes from questions that are easy to get right by accident: the
"no data" edge cases (Q48, Q50), and Q42–44, whose expected answer is "Agência Espacial
Brasileira".

### Per question (round 2)

✓ matched · ~ text check passed · ✗ not matched / needs review · E errored

| Q | Category | qwen3-8b-nothink | qwen3-8b-think | ministral-8b | llama-3.1-8b | phi-4-mini | gemma-3-4b | granite-3.1-8b | xlam-2-8b | Passed |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | single-lookup | ✓ | ✗ | ✓ | ✗ | ✗ | E | ✗ | ✓ | 3 |
| 2 | single-lookup | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 1 |
| 3 | single-lookup | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 2 |
| 4 | single-lookup | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | 2 |
| 5 | single-lookup | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 0 |
| 6 | single-lookup | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 1 |
| 7 | single-lookup | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | 3 |
| 8 | single-lookup | ✓ | ✓ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 2 |
| 9 | single-lookup | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 2 |
| 10 | single-lookup | ✓ | ✓ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 2 |
| 11 | single-lookup | ✓ | ✗ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 1 |
| 12 | single-lookup | ✓ | ✗ | ✗ | ✗ | E | ✗ | ✗ | ✗ | 1 |
| 13 | single-lookup | ✓ | ✓ | ✗ | E | ✗ | ✗ | ✗ | ✗ | 2 |
| 14 | single-lookup | ✓ | ✓ | ✗ | ✗ | E | E | ✗ | ✗ | 2 |
| 15 | single-lookup | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | 3 |
| 16 | single-lookup | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | E | 3 |
| 17 | single-lookup | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 2 |
| 18 | single-lookup | ✗ | ✓ | ✓ | ✗ | E | ✗ | ✗ | ✗ | 2 |
| 19 | single-lookup | ✓ | ✗ | ✗ | E | ✗ | ✗ | ✗ | ✗ | 1 |
| 20 | single-lookup | ✓ | ✓ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 2 |
| 21 | calculation | ✓ | ✓ | ✗ | E | ✗ | ✗ | ✗ | ✗ | 2 |
| 22 | calculation | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 2 |
| 23 | calculation | ✓ | ✓ | ✗ | ✗ | ✗ | E | ✗ | E | 2 |
| 24 | calculation | ✓ | ✓ | ✓ | ✓ | ✗ | E | ✗ | ✗ | 4 |
| 25 | calculation | ✓ | ✓ | ✗ | ✗ | ✗ | E | ✗ | E | 2 |
| 26 | calculation | ✓ | ✓ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 2 |
| 27 | calculation | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 2 |
| 28 | calculation | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | E | 2 |
| 29 | calculation | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 2 |
| 30 | calculation | ✗ | E | ✗ | ✗ | ✗ | ✗ | ✗ | E | 0 |
| 31 | calculation | ✗ | ✓ | ✗ | ✗ | ✗ | E | ✗ | E | 1 |
| 32 | calculation | ~ | ~ | ✗ | ✗ | ✗ | E | ✗ | E | 2 |
| 33 | calculation | ✗ | ~ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 1 |
| 34 | calculation | ~ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 2 |
| 35 | calculation | ✗ | ✓ | ✗ | E | ✗ | ✗ | ✗ | ✗ | 1 |
| 36 | calculation | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | E | 3 |
| 37 | calculation | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 1 |
| 38 | multiple-files | ~ | ~ | ~ | ✗ | ~ | ✗ | ✗ | ✗ | 4 |
| 39 | multiple-files | ~ | ~ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 2 |
| 40 | multiple-files | ~ | ~ | ✗ | E | ✗ | ✗ | ✗ | ✗ | 2 |
| 41 | multiple-files | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 1 |
| 42 | multiple-files | ~ | ~ | ✗ | ✗ | ✗ | ~ | ✗ | E | 3 |
| 43 | multiple-files | ~ | ~ | ✗ | ✗ | ✗ | ~ | ✗ | ~ | 4 |
| 44 | multiple-files | ~ | ~ | ~ | ~ | ✗ | ✗ | ~ | E | 5 |
| 45 | multiple-files | ~ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | E | 2 |
| 46 | multiple-files | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | E | 1 |
| 47 | single-lookup | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 1 |
| 48 | edge-cases | ✗ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | 5 |
| 49 | edge-cases | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 0 |
| 50 | edge-cases | ✓ | E | ✗ | ✓ | ✓ | ✗ | ✓ | E | 4 |

No model passes Q5, Q30 or Q49 (the clarification question). Qwen3 without thinking also misses
Q48, a "no data" question that thinking on, and four of the weak models, get right.

## Round 1: same models, vLLM's default guided decoding

Round 1 ran with vLLM's default structured-output settings, which allow free whitespace inside the
forced JSON. Partway through, a 2,048-token output cap was added for the remaining models (Phi-4-mini,
Gemma, xLAM, Ministral). The two Qwen3 configurations, Llama and Granite ran with no cap.

| Model | Run id | Official | Combined | Errored | Token-limit errors (`UnexpectedModelBehavior`) |
|---|---|---|---|---|---|
| qwen3-8b-nothink | `20261009T095658735183Z` | 30/50 (60%) | 42/50 (84%) | 0 | 0 |
| qwen3-8b-think | `20261009T095054398311Z` | 25/50 (50%) | 35/50 (70%) | 2 | 1 |
| ministral-8b | `20261009T114551423097Z` | 3/50 (6%) | 3/50 (6%) | 0 | 0 |
| llama-3.1-8b | `20261009T101645040343Z` | 4/50 (8%) | 6/50 (12%) | 6 | 0 |
| phi-4-mini | `20261009T110053425396Z` | 4/50 (8%) | 6/50 (12%) | 9 | 7 |
| gemma-3-4b | `20261009T111945612354Z` | 0/50 (0%) | 0/50 (0%) | 37 | 31 |
| granite-3.1-8b | `20261009T102112450820Z` | 3/50 (6%) | 4/50 (8%) | 0 | 0 |
| xlam-2-8b | `20261009T113020443440Z` | 1/50 (2%) | 2/50 (4%) | 27 | 13 |

The token-limit errors were whitespace runaways: the guided JSON let the model emit whitespace
until the output budget ran out. A 3-question Gemma test confirmed it. With
`disable_any_whitespace` on, all 23 of its generations finished as normal tool calls. Fixing it
moved Gemma from 0 to 4 combined and cut its errors from 37 to 14 (the remaining 14 are tool-call
loops that overflow the 40,960-token context). xLAM's errors went from 27 to 13. The Qwen3 runs were
unaffected (identical answers in both rounds).

Not used: two invalid Ministral runs, `20261009T105300579504Z` and `20261009T113730955624Z`.
Every question errored with the `$defs` grammar bug described above.

## Failure modes seen in the traces

- **granite-3.1-8b**: on 36/50 questions (round 1) it calls `final_result` straight away with
  an invented answer ("R$ 12.345,67", "desconhecido"). It barely uses the data tools (1.5 steps
  per question).
- **llama-3.1-8b**: invents round numbers ("R$ 1.234.567,89" twice, "R$ 0,00") and leaves
  placeholders unfilled ("[nome_acao]"). It loops on `discover_data_sources`/`inspect_schema`
  until the step limit, and garbles accents ("oramento", "complementaÇÃo"). It also hit 4
  rejected parallel tool calls in round 1: vLLM's Llama template allows one call per turn.
- **phi-4-mini**: mixes languages ("Selon a base de données", "imposible"), returns status text
  as the answer ("Query sent… waiting for aggregation results"), and gets near-miss numbers.
- **ministral-8b**: often answers in English, sometimes with garbage ("центра", an arXiv link),
  and uses the most steps (7.1 per question) without converging.
- **xlam-2-8b**: leaves out the required `op` discriminator in `query_rows` filters
  (ValidationError), and answers "R$ 0,00" when a query comes back empty instead of reporting
  missing data.
- **gemma-3-4b**: calls the tools with plausible arguments, then keeps calling them until the
  conversation passes 40,960 tokens (13 errors).

A common thread: `query_rows` and `aggregate_rows` have the agent's largest tool schemas (about
1.7k and 3.6k characters of JSON Schema) and use `$defs` plus discriminated `oneOf` filter unions.
Every model except Qwen3 struggled to fill them in correctly. If small non-Qwen models need to be
supported, flatter tool schemas are the first thing to try.

## Caveats

- **One configuration per model, run once.** Generation is deterministic (seed 0), so a rerun gives
  the same numbers. The variability is sensitivity to inputs: earlier 10-question Qwen3 runs on
  older code ranged 40–70%. Treat per-category differences of 1–2 questions as noise.
- **Quantization differs.** AWQ (Qwen3, Llama, Ministral), GPTQ-style W4A16 (Granite), RTN W4A16
  (xLAM) and FP8 (Phi-4-mini, Gemma). The 4B-class models got more precision than the 8B ones.
- **The prompt (`v2`) and the tool descriptions were developed against Qwen3-8B.** The comparison
  measures "which model works with this agent as it is", not general model ability.
- **The text check is provisional.** It is a normalized substring check. It reads every pass for
  qwen3-8b-nothink correctly (checked by hand), but a correct paraphrase fails it, and Q42–44 can
  be passed by guessing "Agência Espacial Brasileira".
