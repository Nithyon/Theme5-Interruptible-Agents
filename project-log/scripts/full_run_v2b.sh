#!/usr/bin/env bash
# Full 100-recording FDB-v3 run of config v2 (Smart Turn OFF) on the SECOND LiveKit project
# (~/theme5/lk2.env), beside run v3st. Never deletes the shared /tmp logs; own gate log dir and port.
set -uo pipefail
P=gate_gemini38_v2b
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
set -a; source ~/theme5/lk2.env; set +a          # exported values win over .env.local (load_dotenv does not override)
export GATE_COMBINE=either GATE_JEV=1 GATE_DRAFT_HOLD_S=2.5 GATE_DANGLING=1 GATE_PROMPT=2 GATE_QUIET_S=0.9 GATE_HESITANT_QUIET_S=1.8 GATE_LEAN=1 GATE_BACKCHANNEL=1 GATE_RETRACT=1 GATE_ID_NORMALIZE=1 GATE_SMART_TURN=0
export GATE_LOG_DIR=/tmp/runb AGENT_PORT=8082
mkdir -p /tmp/runb; rm -f /tmp/runb/gate_*.log
OUT=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_full_${P}
mkdir -p "$OUT"
echo "start $(date)" > "$OUT/run.txt"
echo "config V2 (final config + lean gate + backchannel + retraction + ID rule; Smart Turn off), full fresh run on a second LiveKit project in parallel with v3st: GATE_COMBINE=either GATE_JEV=1 GATE_DRAFT_HOLD_S=2.5 GATE_DANGLING=1 GATE_PROMPT=2 quiet 0.9/1.8 GATE_LEAN=1 GATE_BACKCHANNEL=1 GATE_RETRACT=1 GATE_ID_NORMALIZE=1 GATE_SMART_TURN=0" >> "$OUT/run.txt"
LK_PROVIDER=$P python /mnt/d/Theme5-Interruptible-Agents/fdb_agent/gate_agent_b.py start > "$OUT/agent.log" 2>&1 &
AGENT=$!
sleep 20
if [ "${SMOKE:-0}" = "1" ]; then
  python run_tool_benchmark.py --provider "$P" --example ecommerce_01 --force > "$OUT/smoke_inference.log" 2>&1
  echo "registered: $(grep -c 'registered worker' "$OUT/agent.log")  bind errors: $(grep -c 'address already in use' "$OUT/agent.log")"
  tail -4 "$OUT/smoke_inference.log"; tail -1 /tmp/runb/gate_stats.log | cut -c1-300
  kill $AGENT; sleep 3; kill -9 $AGENT 2>/dev/null; exit 0
fi
python run_tool_benchmark_all_released.py --provider "$P" --force > "$OUT/inference.log" 2>&1
echo "inference exit $? at $(date)" >> "$OUT/run.txt"
kill $AGENT 2>/dev/null; sleep 3; kill -9 $AGENT 2>/dev/null
cp /tmp/runb/gate_stats.log /tmp/runb/gate_events.log "$OUT/" 2>/dev/null
grep -F -f <(grep -ho '"room_name": "[^"]*"' fdb_v3_data_released/*/result_${P}.json | cut -d'"' -f4) /tmp/agent_tool_calls.log > "$OUT/agent_tool_calls.log" 2>/dev/null
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/score_summary.sh "$P" "$OUT" | tee "$OUT/score.txt"
echo "done $(date)" >> "$OUT/run.txt"
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/judge_score.sh "$P" "$OUT" | tee "$OUT/score_geminijudge.txt"
