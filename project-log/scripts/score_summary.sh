#!/usr/bin/env bash
# Score existing results for a provider and print only summary numbers (no expected
# answers). Usage: score_summary.sh <provider> [outdir]
PROVIDER=${1:-gemini3_1}
OUT=${2:-/tmp}
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
EXTRA=""; grep -q '^OPENAI_API_KEY=.\+' .env.local 2>/dev/null && EXTRA="--use-llm"
set -a; source .env.local; set +a
python evaluate_pass_rate.py --benchmark benchmark_data_v2.json --results-dir fdb_v3_data_released \
  --provider "$PROVIDER" --output "$OUT/${PROVIDER}_pass_rate_report.json" $EXTRA > "$OUT/${PROVIDER}_eval.log" 2>&1
echo "judge: ${EXTRA:-exact-match (no OpenAI key)}"
python - "$OUT/${PROVIDER}_pass_rate_report.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
print("evaluated:", r.get("total"), "| passed:", r.get("passed"), "| pass rate:", r.get("overall_pass_rate"))
fails = [x.get("failure_reason", "")[:60] for x in r.get("results", r.get("scenarios", [])) if not x.get("passed")]
kinds = {}
for f in fails:
    k = f.split(":")[0]
    kinds[k] = kinds.get(k, 0) + 1
print("failure kinds:", kinds)
PY
