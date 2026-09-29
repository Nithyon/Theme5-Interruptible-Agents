#!/usr/bin/env bash
~/theme5/fdb-env/bin/python /mnt/d/Theme5-Interruptible-Agents/devset/eval_decisions.py > /tmp/dec.txt 2>&1
~/theme5/fdb-env/bin/python - <<'PY'
import json
r = json.load(open("/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-29_decision_eval.json"))
t = r["turn_state"]
print({k: v for k, v in t.items() if k not in ("per_item", "confusion")})
print("followup:", {k: v for k, v in r["followup"].items()})
PY
