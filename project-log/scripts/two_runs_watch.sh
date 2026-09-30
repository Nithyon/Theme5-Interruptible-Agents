#!/usr/bin/env bash
# Read-only watch for two benchmark runs sharing one laptop: progress, silent recordings, load signs.
date -u '+now %H:%M UTC'; echo "load average: $(cut -d' ' -f1-3 /proc/loadavg) on $(nproc) cores"
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/silent_rooms.sh | sed -n '/silent recordings/,$p'
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs
for d in 2026-09-30_full_gate_gemini38_v3st 2026-09-30_full_gate_gemini38_v2b; do
  L=$R/$d/agent.log; [ -f $L ] || { echo "$d: no agent.log"; continue; }
  now=$(date -u +%H:%M); prev=$(date -u -d '-1 min' +%H:%M); prev2=$(date -u -d '-2 min' +%H:%M)
  echo "$d: WARNING-level lines stamped in the last 3 minutes: $(grep "T$prev2:\|T$prev:\|T$now:" $L | grep -c '"level": "WARNING"') | cgroup-load warnings total: $(grep -c 'impossible cgroup cpu usage' $L) | 'no stream available': $(grep -c 'no stream available' $L) | assignment timeouts: $(grep -c AssignmentTimeoutError $L)"
done
