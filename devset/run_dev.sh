#!/usr/bin/env bash
# Run our own agent against the synthetic dev set (devset/audio/), reusing the benchmark's
# own batch runner in "released layout" mode instead of the real 100 test recordings.
#
# WRITE-ONLY DRAFT: not run in this session (the gate run was using the GPU). Run it
# yourself once devset/audio/ exists (via devset/make_audio.py, in its own tts-env) and the
# gate run has finished — never run this at the same time as a real benchmark run; they
# share /tmp/agent_tool_calls.log and the same LiveKit project.
#
# Usage: run_dev.sh <provider> <agent_script>
#   e.g. run_dev.sh dev_gate_gemini38 /mnt/d/Theme5-Interruptible-Agents/fdb_agent/gate_agent.py
set -uo pipefail

PROVIDER=${1:-dev_gate_gemini38}
AGENT_SCRIPT=${2:-/mnt/d/Theme5-Interruptible-Agents/fdb_agent/gate_agent.py}
DEVSET_DIR=/mnt/d/Theme5-Interruptible-Agents/devset/audio
OUT=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_dev_${PROVIDER}

source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3

if [ ! -d "$DEVSET_DIR" ] || [ -z "$(ls -A "$DEVSET_DIR" 2>/dev/null)" ]; then
  echo "no audio found in $DEVSET_DIR — run devset/make_audio.py first (in ~/theme5/tts-env)" >&2
  exit 1
fi

mkdir -p "$OUT"
rm -f /tmp/agent_tool_calls.log /tmp/agent_heartbeat.log
echo "start $(date)" > "$OUT/run.txt"

LK_PROVIDER=$PROVIDER python "$AGENT_SCRIPT" start > "$OUT/agent.log" 2>&1 &
AGENT=$!
sleep 20

# --root_dir points the released-layout runner at our synthetic folder instead of
# fdb_v3_data_released/; it loads benchmark_data_v2.json if present (it won't be, here) and
# falls back to {} then merges every devset folder's own metadata.json on top — no FDB-v3
# data file is read or needed for this run.
python run_tool_benchmark_all_released.py --provider "$PROVIDER" --root_dir "$DEVSET_DIR" \
  --force > "$OUT/inference.log" 2>&1
echo "inference exit $? at $(date)" >> "$OUT/run.txt"

kill $AGENT 2>/dev/null; sleep 3; kill -9 $AGENT 2>/dev/null
cp /tmp/agent_tool_calls.log /tmp/agent_heartbeat.log "$OUT/" 2>/dev/null

echo "scoring against devset/scenarios.jsonl..."
python /mnt/d/Theme5-Interruptible-Agents/devset/score_dev.py \
  --provider "$PROVIDER" --devset-dir "$DEVSET_DIR" | tee "$OUT/score.txt"

echo "done $(date)" >> "$OUT/run.txt"
echo "logs in $OUT"
