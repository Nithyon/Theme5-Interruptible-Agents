"""Summarize /tmp/gate_events.log without printing any user text (safe on benchmark items)."""
import collections, json, sys
f = sys.argv[1] if len(sys.argv) > 1 else "/tmp/gate_events.log"
for line in open(f):
    r = json.loads(line); ev = r["events"]
    kinds = collections.Counter(e["kind"] for e in ev)
    t0 = ev[0]["t"] if ev else 0
    tl = [(round(e["t"] - t0, 2), e["kind"] + ("*" if e.get("final") else ""), e.get("followup", ""), e.get("held_s", ""))
          for e in ev if e["kind"] != "transcript" or e.get("final")]
    print(r["room"], dict(kinds))
    print("   timeline:", tl[:14])
