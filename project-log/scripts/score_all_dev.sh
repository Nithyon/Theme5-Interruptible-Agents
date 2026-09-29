#!/usr/bin/env bash
cd /mnt/d/Theme5-Interruptible-Agents/devset
for L in "$@"; do
  echo "== $L"
  ~/theme5/fdb-env/bin/python score_dev.py --provider "dev_gate_gemini38_$L" > /tmp/score_$L.txt 2>&1
  grep -E 'strict pass|must_not' /tmp/score_$L.txt
  echo "pause set (p01-p12): $(grep -E '^p[0-9]+_' /tmp/score_$L.txt | grep -c PASS)/12"
done
