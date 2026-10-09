#!/usr/bin/env bash
# Rebuilds the comparison tables and answer sheets in this folder from the run files in
# runs/. Run from anywhere; uses the repository's .venv.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../../.." && pwd)"
compare() { "$repo/.venv/bin/python" "$repo/specs/010-model-comparison/compare_models.py" "$@"; }

round1=(qwen3-8b-nothink=20261009T095658735183Z qwen3-8b-think=20261009T095054398311Z
        ministral-8b=20261009T114551423097Z llama-3.1-8b=20261009T101645040343Z
        phi-4-mini=20261009T110053425396Z gemma-3-4b=20261009T111945612354Z
        granite-3.1-8b=20261009T102112450820Z xlam-2-8b=20261009T113020443440Z)
round2=(qwen3-8b-nothink=20261009T120950189471Z qwen3-8b-think=20261009T130608039025Z
        ministral-8b=20261009T123506627415Z llama-3.1-8b=20261009T125159578786Z
        phi-4-mini=20261009T121744272116Z gemma-3-4b=20261009T124147889923Z
        granite-3.1-8b=20261009T121224424240Z xlam-2-8b=20261009T122923158060Z)

for round in 1 2; do
  name="round$round[@]"
  { echo "# Round $round: comparison"; echo
    compare --runs-dir "$here/runs/round$round" "${!name}"; } > "$here/comparison-round$round.md"
  { echo "# Round $round: every answer"; echo
    echo "Grades: ✓ matched · ~ text check passed (provisional, see compare_models.py) · ✗ not matched or needs review · E errored."
    echo
    compare --runs-dir "$here/runs/round$round" --answers "${!name}"; } > "$here/answers-round$round.md"
done
