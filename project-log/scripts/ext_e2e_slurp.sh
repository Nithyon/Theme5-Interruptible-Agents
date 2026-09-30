#!/usr/bin/env bash
# Home assistant on REAL recordings from the SLURP test set (light-control requests), with the
# lights tool made to fail on its first attempt so the recovery layer has to retry.
# Usage: ext_e2e_slurp.sh [fail_first: 1|0]   (1 = failures injected, 0 = tool never fails)
set -uo pipefail
FAIL=${1:-1}
P=ext_home_slurp
CLIP=${CLIP:-audio_slurp}   # CLIP=audio_slurp_pauses for the version with mid-request pauses
A=/mnt/d/Theme5-Interruptible-Agents/extension/e2e/$CLIP
OUT=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_ext_home_${CLIP#audio_}_fail$FAIL
LOG=/tmp/ext_slurp_events.log
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
set -a; source .env.local; set +a
mkdir -p "$OUT"; rm -f "$LOG"
echo "start $(date -u)" > "$OUT/run.txt"
echo "EXT_PACK=home EXT_SEED=0 EXT_LIGHTS_FAIL_FIRST=$FAIL provider=$P clip=$(ls $A)" >> "$OUT/run.txt"
EXT_EVENT_LOG=$LOG EXT_LIGHTS_FAIL_FIRST=$FAIL EXT_PACK=home EXT_SEED=0 LK_PROVIDER=$P \
  python /mnt/d/Theme5-Interruptible-Agents/extension/ext_agent.py start > "$OUT/agent.log" 2>&1 &
AGENT=$!
sleep 20
python run_tool_benchmark_all_released.py --provider "$P" --root_dir "$A" --force > "$OUT/inference.log" 2>&1
echo "inference exit $? at $(date -u)" >> "$OUT/run.txt"
sleep 6; kill $AGENT 2>/dev/null; sleep 4; kill -9 $AGENT 2>/dev/null
cp "$LOG" "$OUT/ext_recovery_events.log" 2>/dev/null
F=$(ls -d $A/*/ | head -1)
cp "$F"result_$P.json "$OUT/result.json" 2>/dev/null; cp "$F"output_$P.wav "$OUT/agent_reply.wav" 2>/dev/null; cp "$F"metadata.json "$OUT/" 2>/dev/null
echo "== files: $(ls $OUT | tr '\n' ' ')"
echo "== agent log: registered worker $(grep -c 'registered worker' $OUT/agent.log) | errors $(grep -c '"level": "ERROR"' $OUT/agent.log) | tracebacks $(grep -c '^Traceback' $OUT/agent.log)"
python /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/slurp_score.py "$OUT"
