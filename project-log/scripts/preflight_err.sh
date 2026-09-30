#!/usr/bin/env bash
# Read-only: what exactly failed in the talk-mode preflight, and is the benchmark still healthy?
for n in gate car home; do
  f=/tmp/demo/pre_$n.clean
  [ -f "$f" ] || { echo "== $n: not finished yet"; continue; }
  echo "== $n"
  tr -d '\n' < "$f" | grep -o -i '[^ ]\{0,60\}\(permission_denied\|unauthenticated\|quota\|resource_exhausted\)[^"]\{0,240\}' | head -3
  tr -d '\n' < "$f" | grep -o '[A-Za-z.]*\(Error\|Exception\): [^"\]\{0,200\}' | grep -v termios | sort | uniq -c | head -5
done
echo "== still running from preflight: $(pgrep -fc 'console')"
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/run_health.sh
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-30_full_gate_gemini38_v2
echo "benchmark agent log, gemini errors: $(grep -ci 'resource_exhausted\|quota\|429' $R/agent.log)"
