"""Why did the same tool run twice? Uses only our agent's calls and the gate's decision log
(no user text, no expected answers)."""
import collections, json, sys
f = sys.argv[1]
cases = 0; reasons = collections.Counter()
for line in open(f):
    r = json.loads(line); ev = r["events"]
    ex = [e for e in ev if e["kind"] == "execute"]
    prop = {e["seq"]: e for e in ev if e["kind"] == "proposed"}
    by_tool = collections.defaultdict(list)
    for e in ex:
        by_tool[prop[e["seq"]]["name"]].append(e)
    for tool, runs in by_tool.items():
        if len(runs) < 2:
            continue
        cases += 1
        a, b = runs[0], runs[1]
        pa, pb = prop[a["seq"]], prop[b["seq"]]
        same_args = json.dumps(pa["args"], sort_keys=True).lower() == json.dumps(pb["args"], sort_keys=True).lower()
        sta = [e for e in ev if e["kind"] == "same_tool_again" and e.get("new") == b["seq"]]
        first_ran_before_second_proposed = a["t"] <= pb["t"]
        gap = round(pb["t"] - pa["t"], 2)
        if sta:
            why = f"gate saw it, decided {sta[0].get('followup')} via {sta[0].get('source')} → kept both"
        elif first_ran_before_second_proposed:
            why = f"first call already executed (held {a.get('held_s')}s) before the 2nd was proposed"
        else:
            why = "overlap without a same_tool_again decision"
        key = ("already executed" if "already executed" in why else "gate kept both" if "kept both" in why else "other")
        reasons[key] += 1
        diff = {k: (pa['args'].get(k), pb['args'].get(k)) for k in set(pa["args"]) | set(pb["args"]) if pa["args"].get(k) != pb["args"].get(k)}
        print(f"{r['room'][-8:]} {tool:22s} gap {gap:5}s | args differ in: {list(diff) if diff else 'nothing (identical)'} | {why}")
print(f"\ncases: {cases} | {dict(reasons)}")
