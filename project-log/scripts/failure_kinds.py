"""Aggregate failure kinds from a pass-rate report without printing expected values.
Usage: failure_kinds.py <pass_rate_report.json> <provider>"""
import collections, json, pathlib, re, sys
r = json.load(open(sys.argv[1])); prov = sys.argv[2]
kinds = collections.Counter(); by_dom = collections.defaultdict(collections.Counter)
for s in r["scenario_results"]:
    if s["passed"]:
        continue
    reason = (s.get("failure_reason") or "").lower()
    k = ("missing+unexpected tools" if "missing" in reason and "unexpected" in reason else
         "unexpected (extra) tools" if "unexpected" in reason else
         "missing tools" if "missing" in reason else
         "wrong arguments" if "argument" in reason else "other")
    kinds[k] += 1; by_dom[s["domain"]][k] += 1
print("failure kinds:", dict(kinds))
for d, c in sorted(by_dom.items()):
    print(f"  {d}: {dict(c)}")
# our agent's own behaviour (no expected values): repeated calls, no-call runs, latency
D = pathlib.Path.home() / "theme5/Full-Duplex-Bench/v3/fdb_v3_data_released"
dup = none = n = 0; lat = []; first = []
for f in D.glob(f"*/result_{prov}.json"):
    x = json.load(open(f)); n += 1
    calls = [c.get("function") for c in x.get("actual_tool_calls", [])]
    none += not calls
    dup += len(calls) != len(set(calls))
    if isinstance(x.get("perceived_total_latency"), (int, float)): lat.append(x["perceived_total_latency"])
    fs = (x.get("latency") or {}).get("first_speech_s")
    if isinstance(fs, (int, float)): first.append(fs)
med = lambda v: sorted(v)[len(v)//2] if v else None
print(f"runs: {n} | no tool call at all: {none} | same tool called more than once: {dup}")
print(f"perceived latency median: {med(lat)} s (n={len(lat)}) | first speech median: {med(first)} s")
