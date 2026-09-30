#!/usr/bin/env bash
# Show what the recovery layer did in the last extension demo (one line per event).
python3 - <<'PY'
import json, os
p = "/tmp/ext_recovery_events.log"
if not os.path.exists(p):
    print("no recovery log yet: stop the agent with Ctrl+C first"); raise SystemExit
for line in open(p):
    line = line.strip()
    if not line: continue
    try: e = json.loads(line)
    except ValueError: print(line[:160]); continue
    kind = e.get("kind", "?")
    rest = {k: v for k, v in e.items() if k not in ("kind", "seq", "t", "ts", "time") and v not in (None, "", {}, [])}
    print(f"{kind:14}", json.dumps(rest)[:150])
PY
