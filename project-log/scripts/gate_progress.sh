#!/usr/bin/env bash
P=${1:-gate_gemini38}
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_full_$P
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/progress.sh "$P"
cat "$R/run.txt" 2>/dev/null
python3 - <<'PY'
import json, os
f = "/tmp/gate_stats.log"
if os.path.exists(f):
    s = [json.loads(l) for l in open(f) if l.strip()]
    print("gate totals over", len(s), "rooms:", {k: sum(x.get(k, 0) for x in s) for k in ("proposed", "executed", "superseded", "duplicate")})
else:
    print("no gate stats yet")
PY
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/agent_errors.sh "$R/agent.log" | grep -vE 'closed unexpectedly|pass-through' | cut -c1-250
