# Round 2: comparison

## Runs

| Model | Run id | model_name | prompt |
|---|---|---|---|
| qwen3-8b-nothink | `20261009T120950189471Z` | `qwen3-8b-nothink` | v2 |
| qwen3-8b-think | `20261009T130608039025Z` | `Qwen/Qwen3-8B-AWQ` | v2 |
| ministral-8b | `20261009T123506627415Z` | `ministral-8b` | v2 |
| llama-3.1-8b | `20261009T125159578786Z` | `llama-3.1-8b` | v2 |
| phi-4-mini | `20261009T121744272116Z` | `phi-4-mini` | v2 |
| gemma-3-4b | `20261009T124147889923Z` | `gemma-3-4b` | v2 |
| granite-3.1-8b | `20261009T121224424240Z` | `granite-3.1-8b` | v2 |
| xlam-2-8b | `20261009T122923158060Z` | `xlam-2-8b` | v2 |

## Summary

| Model | Official | matched / not / review / err | Text check | Combined | single-lookup | calculation | multiple-files | edge-cases | Errors by type | Steps/q | Retried |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **qwen3-8b-nothink** | 30/50 (60%) | 30 / 7 / 13 / 0 | 12/13 | **42/50 (84%)** | 19/21 | 13/17 | 9/9 | 1/3 | – | 5.6 | 0 |
| **qwen3-8b-think** | 25/50 (50%) | 25 / 10 / 13 / 2 | 10/13 | **35/50 (70%)** | 12/21 | 15/17 | 7/9 | 1/3 | UnexpectedModelBehavior 1, ValidationError 1 | 2.2 | 0 |
| **ministral-8b** | 5/50 (10%) | 5 / 32 / 13 / 0 | 2/13 | **7/50 (14%)** | 2/21 | 2/17 | 2/9 | 1/3 | – | 7.1 | 0 |
| **llama-3.1-8b** | 3/50 (6%) | 3 / 30 / 12 / 5 | 1/12 | **4/50 (8%)** | 1/21 | 1/17 | 1/9 | 1/3 | BadRequestError 5 | 4.1 | 0 |
| **phi-4-mini** | 3/50 (6%) | 3 / 31 / 13 / 3 | 1/13 | **4/50 (8%)** | 1/21 | 0/17 | 1/9 | 2/3 | ValidationError 3 | 4.1 | 0 |
| **gemma-3-4b** | 2/50 (4%) | 2 / 24 / 10 / 14 | 2/10 | **4/50 (8%)** | 1/21 | 0/17 | 2/9 | 1/3 | BadRequestError 13, UsageLimitExceeded 1 | 4.3 | 0 |
| **granite-3.1-8b** | 2/50 (4%) | 2 / 35 / 13 / 0 | 1/13 | **3/50 (6%)** | 0/21 | 0/17 | 1/9 | 2/3 | – | 1.5 | 0 |
| **xlam-2-8b** | 2/50 (4%) | 2 / 27 / 8 / 13 | 1/8 | **3/50 (6%)** | 2/21 | 0/17 | 1/9 | 0/3 | UnexpectedModelBehavior 2, UsageLimitExceeded 5, ValidationError 6 | 3.2 | 0 |

## Per question

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
