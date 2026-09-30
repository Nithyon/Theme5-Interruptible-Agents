#!/usr/bin/env bash
# Copy today's per-recording result files (our agent's outputs only) into their run folders.
D=~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs
for pair in gate_gemini38_v2b:2026-09-30_full_gate_gemini38_v2b gate_gemini38_v3st:2026-09-30_full_gate_gemini38_v3st gate_gemini38_v2:2026-09-30_full_gate_gemini38_v2; do
  P=${pair%%:*}; out=$R/${pair##*:}/per_recording; mkdir -p "$out"; n=0
  for f in "$D"/*/result_$P.json; do [ -f "$f" ] || continue; cp "$f" "$out/$(basename "$(dirname "$f")").json"; n=$((n+1)); done
  echo "$P: $n result files -> ${pair##*:}/per_recording"
done
[ -d /tmp/runb ] && cp -n /tmp/runb/gate_events.log /tmp/runb/gate_stats.log $R/2026-09-30_full_gate_gemini38_v2b/ 2>/dev/null
ls $R/2026-09-30_full_gate_gemini38_v2b | tr '\n' ' '
