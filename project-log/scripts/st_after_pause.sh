#!/usr/bin/env bash
# Read-only: after Smart Turn said "not finished" (p<0.5), did the user actually say more before the call ran?
python3 - <<'PY'
import json, os
rooms = [json.loads(l) for l in open("/tmp/gate_events.log")]
for i, r in enumerate(rooms, 1):
    ev = r["events"]
    for j, e in enumerate(ev):
        if e["kind"] == "smart_turn" and e.get("p_complete") is not None and e["p_complete"] < 0.5:
            t = e["t"]
            ex = next((x for x in ev[j:] if x["kind"] == "execute"), None)
            end = ex["t"] if ex else t + 5
            later_speech = [x for x in ev[j:] if x["kind"] == "transcript" and x["t"] <= end]
            speaking = [x for x in ev[j:] if x["kind"] == "user_state" and x.get("state") == "speaking" and x["t"] <= end]
            after_exec = [x for x in ev if x["kind"] == "transcript" and ex and x["t"] > ex["t"]]
            last = next((x["text"] for x in reversed(ev[:j]) if x["kind"] == "transcript"), "")
            print(f"room {i}: p={e['p_complete']:.2f} | user's words before the pause end with: ...{last[-60:]!r}")
            print(f"    more user speech before the call ran: transcripts {len(later_speech)}, speech starts {len(speaking)} | user speech after the call ran: {len(after_exec)} transcript events")
PY
