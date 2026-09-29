"""For each 'already executed' repeat: when did the first call run, and when did the user resume speaking?
Timing only (no text)."""
import collections, json, sys
for line in open(sys.argv[1]):
    r = json.loads(line); ev = r["events"]
    prop = {e["seq"]: e for e in ev if e["kind"] == "proposed"}
    ex = [e for e in ev if e["kind"] == "execute"]
    byt = collections.defaultdict(list)
    for e in ex: byt[prop[e["seq"]]["name"]].append(e)
    for tool, runs in byt.items():
        if len(runs) < 2: continue
        a, b = runs[0], runs[1]; pa, pb = prop[a["seq"]], prop[b["seq"]]
        if pb["t"] - pa["t"] < 0.5: continue           # parallel pair (group A)
        speak = [e["t"] for e in ev if e["kind"] == "user_state" and e.get("state") == "speaking" and e["t"] > pa["t"]]
        resume = round(speak[0] - pa["t"], 2) if speak else None
        print(f"{r['room'][-8:]} {tool:20s} first proposed→ran after {a['held_s']}s | user resumed speaking {resume}s after the proposal | 2nd proposal at +{round(pb['t']-pa['t'],2)}s")
