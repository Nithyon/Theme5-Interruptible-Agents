"""Per room: proposals that never executed (held when the session ended), with hold state."""
import json, sys
f = sys.argv[1]
n_rooms = n_lost = 0
for line in open(f):
    r = json.loads(line); ev = r["events"]; n_rooms += 1
    prop = {e["seq"]: e for e in ev if e["kind"] == "proposed"}
    done = {e["seq"] for e in ev if e["kind"] in ("execute", "superseded", "duplicate")}
    lost = [s for s in prop if s not in done]
    if lost:
        n_lost += 1
        last_t = ev[-1]["t"]
        jt = [e["probs"] for e in ev if e["kind"] == "jev_turn"]
        print(r["room"], "| never executed:", [prop[s]["name"] for s in lost],
              "| proposed", round(last_t - prop[lost[0]]["t"], 2), "s before the log ended | last jev:", jt[-1] if jt else None)
print(f"rooms {n_rooms}, rooms with an unexecuted proposal: {n_lost}")
