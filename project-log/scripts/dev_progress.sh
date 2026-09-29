#!/usr/bin/env bash
L=${1:-A}
echo "results: $(ls /mnt/d/Theme5-Interruptible-Agents/devset/audio/*/result_dev_gate_gemini38_$L.json 2>/dev/null | wc -l)/50"
python3 - <<'PY'
import json, os, collections
f = "/tmp/gate_stats.log"
if os.path.exists(f):
    rows = [json.loads(l) for l in open(f) if l.strip()]
    print("rooms:", len(rows), "| with Jev:", sum(1 for r in rows if r.get("jev")),
          "| totals:", {k: sum(r.get(k, 0) for r in rows) for k in ("proposed", "executed", "superseded", "duplicate", "kept_both")})
PY
