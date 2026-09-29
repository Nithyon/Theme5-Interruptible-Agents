"""How Jev influenced the gate in a dev run: turn-state verdicts and hold times (no text)."""
import json, statistics, sys
f = sys.argv[1] if len(sys.argv) > 1 else "/tmp/gate_events.log"
verdicts = {"complete": 0, "continuing": 0, "unsure": 0}; holds = []; stats = []
for line in open(f):
    r = json.loads(line)
    for e in r["events"]:
        if e["kind"] == "jev_turn":
            p = e["probs"]
            v = "complete" if p.get("complete", 0) >= 0.8 else "continuing" if p.get("continuing", 0) >= 0.6 else "unsure"
            verdicts[v] += 1
        if e["kind"] == "execute":
            holds.append(e.get("held_s", 0))
print("Jev turn verdicts:", verdicts)
if holds:
    print(f"tool-call hold: median {statistics.median(holds):.2f} s, max {max(holds):.2f} s, n={len(holds)}")
