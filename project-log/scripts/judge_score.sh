#!/usr/bin/env bash
# Re-score a finished run with the Gemini judge on Vertex (no rerun of the audio).
# Usage: judge_score.sh <provider> <outdir>
PROVIDER=${1:?provider}
OUT=${2:?outdir}
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
set -a; source .env.local; set +a
python /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/judge_vertex.py evaluate_pass_rate \
  --benchmark benchmark_data_v2.json --results-dir fdb_v3_data_released --provider "$PROVIDER" \
  --output "$OUT/${PROVIDER}_pass_rate_report_geminijudge.json" --use-llm \
  > "$OUT/${PROVIDER}_eval_geminijudge.log" 2>&1
grep '^JUDGE' "$OUT/${PROVIDER}_eval_geminijudge.log"
python - "$OUT/${PROVIDER}_pass_rate_report_geminijudge.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
print(f"evaluated: {r.get('total_scenarios')} | passed: {r.get('passed')} | pass rate: {r.get('overall_pass_rate')}")
print("failure breakdown:", r.get("failure_breakdown"))
def rate(d):
    return {k: (f"{v.get('passed')}/{v.get('total')}" if isinstance(v, dict) and 'passed' in v else v) for k, v in (d or {}).items()}
for key in ("by_domain", "by_num_tools", "by_disfluency_feature"):
    print(f"{key}:", rate(r.get(key)))
PY
