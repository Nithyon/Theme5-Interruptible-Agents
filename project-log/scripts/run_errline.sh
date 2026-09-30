#!/usr/bin/env bash
# Show the error-like lines in the final run's inference log (read-only).
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-30_full_gate_gemini38_v2
grep -n -i 'traceback\|error' $R/inference.log | cut -c1-260
echo "--- status values in finished results:"
python3 - <<'PY'
import glob, json, os, collections
c = collections.Counter()
for f in glob.glob(os.path.expanduser("~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released/*/result_gate_gemini38_v2.json")):
    try: c[json.load(open(f)).get("status")] += 1
    except Exception as e: c["unreadable"] += 1
print(dict(c))
PY
