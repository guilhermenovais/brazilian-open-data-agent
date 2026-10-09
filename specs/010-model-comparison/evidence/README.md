# Evidence for the 010 model comparison

Everything `../results.md` is based on. The original run files live in the gitignored
`data/testset_runs/`. The copies here are the record.

| Path | What |
|---|---|
| `answers-round1.md`, `answers-round2.md` | Every model's full answer to every question: grade, reported outcome, tool calls, and the failure for errored questions |
| `comparison-round1.md`, `comparison-round2.md` | Summary and per-question tables from `compare_models.py` |
| `runs/round1/`, `runs/round2/` | The 8 run files of each round (`testset_runner` JSON, including every tool call's arguments and result summary) |
| `runs/invalid/` | Two Ministral runs where every question failed on the vLLM `$defs` grammar bug (see results.md). Not used |
| `runs/gemma-whitespace-test/` | The 3-question Gemma runs (`testset-3-questions.json`, Q2, Q3, Q22) that isolated the whitespace problem, in order: (1) default guided decoding, all token-limit errors; (2) `guidance` backend with `disable_any_whitespace`, which rejects the agent's `oneOf` schemas; (3) invalid, it ran against the still-running server from (2); (4) `xgrammar` with `disable_any_whitespace`, no token-limit errors |
| `logs/` | Logs from `~/llm` (repo: https://github.com/guilhermenovais/open-model-scripts) |
| `regenerate.sh` | Rebuilds the four markdown files above from `runs/` |

The logs are:

- `round1-queue.log` and `round2-queue.log`: each model's start, smoke test and runner summary, in order.
- `<model>.serve.log`, `<model>.smoke.log` and `<model>.run.log`: each model's **last** run, which is round 2. Round 1's per-model logs were overwritten; their summaries are in `round1-queue.log`.
- `gemma-debug*.serve.log`, `ministral-debug.serve.log`: the debugging sessions. `gemma-debug.serve.log` includes the logged requests and outputs of test (1).
- `dl_*.log`: the model downloads.

Notes:

- `[REDACTED]` in failure messages replaces every letter "x". The runs used the API key `x`
  (vLLM ignores it), and the agent's failure redaction removes the key's literal value. Answers
  are not affected.
- Round 1 also had an aborted Gemma run (FP8, no output cap: stopped after its first 7
  questions took about 6 minutes each and failed on the output-token limit), a Phi-4-mini attempt whose server failed to start (bf16 out of
  memory), and an xLAM attempt whose server failed to start (bitsandbytes). None of them produced
  a run file. They show up in `round1-queue.log`.
