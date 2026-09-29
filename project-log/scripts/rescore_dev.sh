#!/usr/bin/env bash
# Re-score finished dev runs over all 62 scenarios into score_all62.txt (keeps the original score.txt).
cd /mnt/d/Theme5-Interruptible-Agents/devset
for L in "$@"; do
  R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-29_dev_dev_gate_gemini38_$L
  ~/theme5/fdb-env/bin/python score_dev.py --provider "dev_gate_gemini38_$L" > "$R/score_all62.txt" 2>&1
  echo "$L: $(grep -E 'strict pass' "$R/score_all62.txt") | $(grep -E 'must_not_call hits' "$R/score_all62.txt" | cut -d'(' -f1)"
done
