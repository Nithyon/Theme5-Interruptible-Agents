"""Map each repeat-call room to its scenario (by matching our executed calls) and print only pass/fail."""
import collections, glob, json, pathlib
R = "/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-29_full_gate_gemini38_final"
P = "gate_gemini38_final"
passed = {s["scenario_id"]: s["passed"] for s in json.load(open(f"{R}/{P}_pass_rate_report.json"))["scenario_results"]}
calls_by_room = collections.defaultdict(list)
for l in open(f"{R}/agent_tool_calls.log"):
    x = json.loads(l); calls_by_room[x["room"]].append((x["call"]["function"], json.dumps(x["call"]["args"], sort_keys=True)))
res = {}
for f in glob.glob(f"/home/saini/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released/*/result_{P}.json"):
    x = json.load(open(f))
    sig = sorted((c.get("function"), json.dumps(c.get("arguments") or c.get("args") or {}, sort_keys=True)) for c in x.get("actual_tool_calls", []))
    res.setdefault(json.dumps(sig), []).append(pathlib.Path(f).parent.name)
out = collections.Counter()
for room, calls in calls_by_room.items():
    names = [c[0] for c in calls]
    if not any(names.count(n) > 1 for n in set(names)):
        continue
    folders = res.get(json.dumps(sorted(calls)), [])
    sids = sorted({"_".join(fo.split("_")[:2]) for fo in folders})
    outcome = sorted({passed.get(s) for s in sids}) if sids else ["?"]
    print(room[-8:], names, "->", sids[:2], "passed:", outcome)
    for o in outcome: out[str(o)] += 1
print(dict(out))
