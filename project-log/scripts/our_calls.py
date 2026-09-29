"""Diagnostics on OUR agent's outputs only (never expected answers).
1) argument shapes per tool in given domains, 2) repeat calls: identical vs different args,
3) rooms with no tool call. Usage: our_calls.py <provider>"""
import collections, json, pathlib, re, sys
prov = sys.argv[1]
D = pathlib.Path.home() / "theme5/Full-Duplex-Bench/v3/fdb_v3_data_released"
def shape(v):
    if v is None or v == "": return "EMPTY"
    if isinstance(v, (int, float)): return "number"
    s = str(v)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s): return "ISO date"
    if re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|next)", s.lower()): return "spoken date/word"
    if re.fullmatch(r"[A-Z]{3}", s): return "3-letter code"
    if re.fullmatch(r"[\d\-\s]+", s): return "digits"
    return f"text({len(s.split())}w)"
shapes = collections.defaultdict(collections.Counter)
rep_same = rep_diff = 0; nocall = []
for f in sorted(D.glob(f"*/result_{prov}.json")):
    dom = f.parent.name.rsplit("_", 2)[0]
    x = json.load(open(f))
    calls = x.get("actual_tool_calls", [])
    if not calls: nocall.append(f.parent.name)
    for c in calls:
        for k, v in (c.get("arguments") or c.get("args") or {}).items():
            shapes[(dom, c.get("function"), k)][shape(v)] += 1
    by = collections.defaultdict(list)
    for c in calls: by[c.get("function")].append(json.dumps(c.get("arguments") or c.get("args") or {}, sort_keys=True).lower())
    for fn, a in by.items():
        if len(a) > 1: rep_same += len(set(a)) < len(a); rep_diff += len(set(a)) > 1
print("== argument shapes (housing / travel)")
for (dom, fn, k), c in sorted(shapes.items()):
    if dom.startswith(("housing", "travel")): print(f"  {dom:18s} {fn}.{k}: {dict(c)}")
print(f"== repeat calls: identical-args groups {rep_same}, different-args groups {rep_diff}")
print("== no tool call:", nocall)
