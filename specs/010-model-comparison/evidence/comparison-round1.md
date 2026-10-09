# Round 1: comparison

## Runs

| Model | Run id | model_name | prompt |
|---|---|---|---|
| qwen3-8b-nothink | `20261009T095658735183Z` | `qwen3-8b-nothink` | v2 |
| qwen3-8b-think | `20261009T095054398311Z` | `Qwen/Qwen3-8B-AWQ` | v2 |
| ministral-8b | `20261009T114551423097Z` | `ministral-8b` | v2 |
| llama-3.1-8b | `20261009T101645040343Z` | `llama-3.1-8b` | v2 |
| phi-4-mini | `20261009T110053425396Z` | `phi-4-mini` | v2 |
| gemma-3-4b | `20261009T111945612354Z` | `gemma-3-4b` | v2 |
| granite-3.1-8b | `20261009T102112450820Z` | `granite-3.1-8b` | v2 |
| xlam-2-8b | `20261009T113020443440Z` | `xlam-2-8b` | v2 |

## Summary

| Model | Official | matched / not / review / err | Text check | Combined | single-lookup | calculation | multiple-files | edge-cases | Errors by type | Steps/q | Retried |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **qwen3-8b-nothink** | 30/50 (60%) | 30 / 7 / 13 / 0 | 12/13 | **42/50 (84%)** | 19/21 | 13/17 | 9/9 | 1/3 | – | 5.6 | 0 |
| **qwen3-8b-think** | 25/50 (50%) | 25 / 10 / 13 / 2 | 10/13 | **35/50 (70%)** | 12/21 | 15/17 | 7/9 | 1/3 | UnexpectedModelBehavior 1, ValidationError 1 | 2.2 | 0 |
| **ministral-8b** | 3/50 (6%) | 3 / 34 / 13 / 0 | 0/13 | **3/50 (6%)** | 1/21 | 2/17 | 0/9 | 0/3 | – | 6.9 | 0 |
| **llama-3.1-8b** | 4/50 (8%) | 4 / 29 / 11 / 6 | 2/11 | **6/50 (12%)** | 2/21 | 1/17 | 2/9 | 1/3 | BadRequestError 5, ValidationError 1 | 3.8 | 0 |
| **phi-4-mini** | 4/50 (8%) | 4 / 27 / 10 / 9 | 2/10 | **6/50 (12%)** | 0/21 | 2/17 | 2/9 | 2/3 | BadRequestError 1, UnexpectedModelBehavior 7, ValidationError 1 | 3.5 | 0 |
| **gemma-3-4b** | 0/50 (0%) | 0 / 7 / 6 / 37 | 0/6 | **0/50 (0%)** | 0/21 | 0/17 | 0/9 | 0/3 | BadRequestError 3, UnexpectedModelBehavior 31, UsageLimitExceeded 3 | 2.0 | 0 |
| **granite-3.1-8b** | 3/50 (6%) | 3 / 34 / 13 / 0 | 1/13 | **4/50 (8%)** | 0/21 | 1/17 | 1/9 | 2/3 | – | 2.7 | 0 |
| **xlam-2-8b** | 1/50 (2%) | 1 / 17 / 5 / 27 | 1/5 | **2/50 (4%)** | 1/21 | 0/17 | 1/9 | 0/3 | UnexpectedModelBehavior 13, UsageLimitExceeded 1, ValidationError 13 | 1.6 | 0 |

## Per question

| Q | Category | qwen3-8b-nothink | qwen3-8b-think | ministral-8b | llama-3.1-8b | phi-4-mini | gemma-3-4b | granite-3.1-8b | xlam-2-8b | Passed |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | single-lookup | ✓ | ✗ | ✗ | ✗ | E | E | ✗ | ✗ | 1 |
| 2 | single-lookup | ✓ | ✗ | ✓ | E | ✗ | E | ✗ | E | 2 |
| 3 | single-lookup | ✓ | ✓ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 2 |
| 4 | single-lookup | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 1 |
| 5 | single-lookup | ✗ | ✗ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 0 |
| 6 | single-lookup | ✓ | ✗ | ✗ | E | ✗ | E | ✗ | ✗ | 1 |
| 7 | single-lookup | ✓ | ✓ | ✗ | ✗ | E | E | ✗ | ✓ | 3 |
| 8 | single-lookup | ✓ | ✓ | ✗ | ✗ | ✗ | E | ✗ | E | 2 |
| 9 | single-lookup | ✓ | ✓ | ✗ | ✓ | ✗ | E | ✗ | ✗ | 3 |
| 10 | single-lookup | ✓ | ✓ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 2 |
| 11 | single-lookup | ✓ | ✗ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 1 |
| 12 | single-lookup | ✓ | ✗ | ✗ | ✗ | ✗ | E | ✗ | E | 1 |
| 13 | single-lookup | ✓ | ✓ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 2 |
| 14 | single-lookup | ✓ | ✓ | ✗ | ✗ | ✗ | E | ✗ | E | 2 |
| 15 | single-lookup | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | E | 2 |
| 16 | single-lookup | ✓ | ✓ | ✗ | ✗ | E | ✗ | ✗ | ✗ | 2 |
| 17 | single-lookup | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | E | 2 |
| 18 | single-lookup | ✗ | ✓ | ✗ | ✗ | ✗ | E | ✗ | E | 1 |
| 19 | single-lookup | ✓ | ✗ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 1 |
| 20 | single-lookup | ✓ | ✓ | ✗ | ✓ | ✗ | E | ✗ | ✗ | 3 |
| 21 | calculation | ✓ | ✓ | ✗ | ✗ | ✗ | E | ✗ | E | 2 |
| 22 | calculation | ✓ | ✓ | ✓ | E | ✓ | E | ✗ | E | 4 |
| 23 | calculation | ✓ | ✓ | ✓ | ✗ | ✗ | E | ✗ | E | 3 |
| 24 | calculation | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | E | 3 |
| 25 | calculation | ✓ | ✓ | ✗ | ✗ | ✗ | E | ✗ | E | 2 |
| 26 | calculation | ✓ | ✓ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 2 |
| 27 | calculation | ✓ | ✓ | ✗ | ✗ | ✓ | E | ✗ | E | 3 |
| 28 | calculation | ✓ | ✓ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 2 |
| 29 | calculation | ✓ | ✓ | ✗ | ✗ | E | E | ✗ | ✗ | 2 |
| 30 | calculation | ✗ | E | ✗ | ✗ | E | E | ✗ | E | 0 |
| 31 | calculation | ✗ | ✓ | ✗ | ✗ | ✗ | E | ✗ | E | 1 |
| 32 | calculation | ~ | ~ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 2 |
| 33 | calculation | ✗ | ~ | ✗ | ✗ | E | ✗ | ✗ | E | 1 |
| 34 | calculation | ~ | ~ | ✗ | ✗ | E | E | ✗ | E | 2 |
| 35 | calculation | ✗ | ✓ | ✗ | E | ✗ | E | ✗ | ✗ | 1 |
| 36 | calculation | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | E | 2 |
| 37 | calculation | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | E | 2 |
| 38 | multiple-files | ~ | ~ | ✗ | ✗ | ~ | ✗ | ✗ | E | 3 |
| 39 | multiple-files | ~ | ~ | ✗ | E | ✗ | ✗ | ✗ | ✗ | 2 |
| 40 | multiple-files | ~ | ~ | ✗ | E | ~ | E | ~ | ✗ | 4 |
| 41 | multiple-files | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | E | 1 |
| 42 | multiple-files | ~ | ~ | ✗ | ~ | E | E | ✗ | ~ | 4 |
| 43 | multiple-files | ~ | ~ | ✗ | ✗ | ✗ | E | ✗ | E | 2 |
| 44 | multiple-files | ~ | ~ | ✗ | ~ | ✗ | ✗ | ✗ | E | 3 |
| 45 | multiple-files | ~ | ~ | ✗ | ✗ | ✗ | ✗ | ✗ | E | 2 |
| 46 | multiple-files | ~ | ✗ | ✗ | ✗ | ✗ | E | ✗ | E | 1 |
| 47 | single-lookup | ~ | ✗ | ✗ | ✗ | ✗ | E | ✗ | ✗ | 1 |
| 48 | edge-cases | ✗ | ✓ | ✗ | ✗ | ✓ | E | ✓ | ✗ | 3 |
| 49 | edge-cases | ✗ | ✗ | ✗ | ✗ | ✓ | E | ✗ | E | 1 |
| 50 | edge-cases | ✓ | E | ✗ | ✓ | E | E | ✓ | E | 3 |
