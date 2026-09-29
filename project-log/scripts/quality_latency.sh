#!/usr/bin/env bash
# A8 + A9 on a finished run: tool accuracy + spoken-answer accuracy (Gemini judge) and latency.
# Usage: quality_latency.sh <provider> <outdir>   (reads saved results only)
P=${1:?provider}; OUT=${2:?outdir}
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
set -a; source .env.local; set +a
python /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/judge_vertex.py evaluate_tool_calls \
  --benchmark benchmark_data_v2.json --results-dir fdb_v3_data_released --provider "$P" \
  --output "$OUT/${P}_evaluation_report_geminijudge.json" --use-llm > "$OUT/${P}_toolcalls_geminijudge.log" 2>&1
grep '^JUDGE' "$OUT/${P}_toolcalls_geminijudge.log"
python analyze_tool_latency.py --results-dir fdb_v3_data_released --provider "$P" > "$OUT/${P}_latency.txt" 2>&1
python - "$OUT/${P}_evaluation_report_geminijudge.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
s = r.get("summary") or r.get("overall") or {k: v for k, v in r.items() if not isinstance(v, (list, dict))}
print("tool/response summary:", json.dumps(s)[:600])
PY
echo "--- latency (tail):"; tail -25 "$OUT/${P}_latency.txt" | grep -vE '^\s*$'
