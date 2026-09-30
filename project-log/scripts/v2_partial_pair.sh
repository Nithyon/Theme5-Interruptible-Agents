#!/usr/bin/env bash
# Pair the 34 v2 recordings with the same recordings in earlier full runs, using pass flags only.
python3 - <<'PY'
import json, collections
R = "/mnt/d/Theme5-Interruptible-Agents/project-log/runs"
def items(p): return json.load(open(p))["scenario_results"]
ident = lambda x: (x["scenario_id"], x["title"], x["domain"], str(x.get("disfluency")), x.get("num_tools"))
v2 = items("/tmp/demo/v2_partial_strict.json")
runs = {
 "final strict": items(f"{R}/2026-09-29_full_gate_gemini38_final/gate_gemini38_final_pass_rate_report.json"),
 "final judged": items(f"{R}/2026-09-29_full_gate_gemini38_final/gate_gemini38_final_pass_rate_report_geminijudge.json"),
 "stock strict": items(f"{R}/2026-09-29_full_gemini3_8/gemini3_8_pass_rate_report.json"),
 "stock judged": items(f"{R}/2026-09-29_full_gemini3_8/gemini3_8_pass_rate_report_geminijudge.json"),
}
print("v2 items:", len(v2), "| unique identities:", len({ident(x) for x in v2}))
for name, full in runs.items():
    print(f"{name}: {len(full)} items | first {len(v2)} have the same identity sequence as v2: {[ident(x) for x in full[:len(v2)]] == [ident(x) for x in v2]}")
n = len(v2)
print("\ndomains of these", n, "recordings:", dict(collections.Counter(x["domain"] for x in v2)))
print("domains of all 100:", dict(collections.Counter(x["domain"] for x in runs["stock strict"])))
print(f"\nSTRICT on the same {n}: v2 {sum(x['passed'] for x in v2)} | yesterday's pipeline {sum(x['passed'] for x in runs['final strict'][:n])} | stock {sum(x['passed'] for x in runs['stock strict'][:n])}")
print(f"JUDGED on the same {n}: yesterday's pipeline {sum(x['passed'] for x in runs['final judged'][:n])} | stock {sum(x['passed'] for x in runs['stock judged'][:n])}")
rest = slice(n, None)
print(f"REMAINING {100-n}: strict pipeline {sum(x['passed'] for x in runs['final strict'][rest])}, stock {sum(x['passed'] for x in runs['stock strict'][rest])} | judged pipeline {sum(x['passed'] for x in runs['final judged'][rest])}, stock {sum(x['passed'] for x in runs['stock judged'][rest])}")
a = [x["passed"] for x in v2]; b = [x["passed"] for x in runs["final strict"][:n]]
print("v2 vs yesterday's pipeline, same recordings (strict): both pass", sum(p and q for p, q in zip(a, b)), "| only v2", sum(p and not q for p, q in zip(a, b)), "| only yesterday", sum(q and not p for p, q in zip(a, b)), "| both fail", sum(not p and not q for p, q in zip(a, b)))
for d in sorted({x["domain"] for x in v2}):
    idx = [i for i, x in enumerate(v2) if x["domain"] == d]
    print(f"  {d}: v2 {sum(a[i] for i in idx)}/{len(idx)} | yesterday {sum(b[i] for i in idx)}/{len(idx)} | stock {sum(runs['stock strict'][i]['passed'] for i in idx)}/{len(idx)}")
PY
