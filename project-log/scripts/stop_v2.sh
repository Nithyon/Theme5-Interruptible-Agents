#!/usr/bin/env bash
# Stop full run v2 (user decision 2026-09-30: rerun with Smart Turn included). Results so far are kept.
pkill -f full_run_v2.sh; sleep 1
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-30_full_gate_gemini38_v2
N=$(find ~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released -name 'result_gate_gemini38_v2.json' | wc -l)
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/stop_run.sh "$R" "STOPPED on purpose after $N/100 recordings (lead asked for a run with Smart Turn included); partial, not scored"
cp /tmp/gate_events.log "$R/" 2>/dev/null; ls "$R"
