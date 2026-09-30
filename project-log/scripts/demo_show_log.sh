#!/usr/bin/env bash
# Show what the gate decided in the last demo conversation (one line per decision).
python3 - <<'PY'
import json
for line in open("/tmp/gate_events.log"):
    for e in json.loads(line)["events"]:
        k = e["kind"]
        if k in ("user_state",): continue
        print(f'{k:16}', {x: y for x, y in e.items() if x not in ("kind", "t")})
PY
echo "--- tool calls that actually ran:"; cat /tmp/agent_tool_calls.log 2>/dev/null
