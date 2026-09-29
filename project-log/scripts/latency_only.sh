#!/usr/bin/env bash
P=${1:?provider}; OUT=${2:?outdir}
source ~/theme5/fdb-env/bin/activate; cd ~/theme5/Full-Duplex-Bench/v3
set -a; source .env.local; set +a
python /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/judge_vertex.py analyze_tool_latency \
  --results-dir fdb_v3_data_released --provider "$P" > "$OUT/${P}_latency.txt" 2>&1
grep -E '^JUDGE' "$OUT/${P}_latency.txt"; grep -vE '^\s*$|HTTP Request' "$OUT/${P}_latency.txt" | tail -30
