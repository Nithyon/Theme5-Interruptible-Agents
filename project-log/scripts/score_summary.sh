#!/usr/bin/env bash
# Score existing results for a provider and print only summary numbers (no expected
# answers). Usage: score_summary.sh <provider> [outdir]
PROVIDER=${1:-gemini3_1}
OUT=${2:-/tmp}
source "${ENV_DIR:-$HOME/theme5/fdb-env}/bin/activate"
cd "${FDB_V3_DIR:-$HOME/theme5/Full-Duplex-Bench/v3}"
EXTRA=""; grep -q '^OPENAI_API_KEY=.\+' .env.local 2>/dev/null && EXTRA="--use-llm"
set -a; source .env.local; set +a
python evaluate_pass_rate.py --benchmark benchmark_data_v2.json --results-dir fdb_v3_data_released \
  --provider "$PROVIDER" --output "$OUT/${PROVIDER}_pass_rate_report.json" $EXTRA > "$OUT/${PROVIDER}_eval.log" 2>&1
echo "judge: ${EXTRA:-exact-match (no OpenAI key)}"
python - "$OUT/${PROVIDER}_pass_rate_report.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
print(f"evaluated: {r.get('total_scenarios')} | passed: {r.get('passed')} | pass rate: {r.get('overall_pass_rate')}")
print("failure breakdown:", r.get("failure_breakdown"))
def rate(d):
    return {k: (f"{v.get('passed')}/{v.get('total')}" if isinstance(v, dict) and 'passed' in v else v) for k, v in (d or {}).items()}
for key in ("by_difficulty", "by_num_tools", "by_disfluency_feature", "by_state_rollback", "by_domain"):
    print(f"{key}:", rate(r.get(key)))
PY
