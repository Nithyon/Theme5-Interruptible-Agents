#!/usr/bin/env bash
# Pair v2's finished recordings with earlier full runs BY RECORDING FOLDER, and refuse to compare
# unless the pairing is verified. Uses pass flags only.
python3 - <<'PY'
import json, os, collections, sys
R = "/mnt/d/Theme5-Interruptible-Agents/project-log/runs"
D = os.path.expanduser("~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released")
def items(p): return json.load(open(p))["scenario_results"]
ident = lambda x: (x["scenario_id"], x["title"], x["domain"], str(x.get("disfluency")), x.get("num_tools"))
folders = sorted(f for f in os.listdir(D) if os.path.isdir(os.path.join(D, f)))
has = lambda f, p: os.path.exists(os.path.join(D, f, f"result_{p}.json"))
v2 = items("/tmp/demo/v2_partial_strict.json")
runs = {
 "pipeline strict": ("gate_gemini38_final", items(f"{R}/2026-09-29_full_gate_gemini38_final/gate_gemini38_final_pass_rate_report.json")),
 "pipeline judged": ("gate_gemini38_final", items(f"{R}/2026-09-29_full_gate_gemini38_final/gate_gemini38_final_pass_rate_report_geminijudge.json")),
 "stock strict": ("gemini3_8", items(f"{R}/2026-09-29_full_gemini3_8/gemini3_8_pass_rate_report.json")),
 "stock judged": ("gemini3_8", items(f"{R}/2026-09-29_full_gemini3_8/gemini3_8_pass_rate_report_geminijudge.json")),
}
print("recording folders:", len(folders), "| with a v2 result:", sum(has(f, "gate_gemini38_v2") for f in folders))
paired = {}
for name, (prov, full) in runs.items():
    fl = [f for f in folders if has(f, prov)]
    if len(fl) != len(full):
        print(f"{name}: folder count {len(fl)} != report items {len(full)} -> cannot pair"); continue
    pos = [i for i, f in enumerate(fl) if has(f, "gate_gemini38_v2")]
    sub = [full[i] for i in pos]
    ok = len(sub) == len(v2) and [ident(x) for x in sub] == [ident(x) for x in v2]
    print(f"{name}: pairing by folder verified = {ok}")
    if ok: paired[name] = sub
if len(paired) < 4:
    # valid without pairing: whole-domain totals (all 29 ecommerce recordings are in v2's set)
    print("\nPAIRING NOT VERIFIED for some reports: no per-recording comparison printed.")
n = len(v2); a = [x["passed"] for x in v2]
print(f"\nv2 alone (strict): {sum(a)}/{n} | by domain:", {d: f"{sum(x['passed'] for x in v2 if x['domain']==d)}/{sum(x['domain']==d for x in v2)}" for d in sorted({x['domain'] for x in v2})})
for name, (prov, full) in runs.items():
    e = [x for x in full if x["domain"] == "ecommerce_support"]
    print(f"whole ecommerce domain, {name}: {sum(x['passed'] for x in e)}/{len(e)}")
for name, sub in paired.items():
    b = [x["passed"] for x in sub]
    print(f"same {n} recordings, {name}: {sum(b)}/{n} | vs v2 strict: both pass {sum(p and q for p,q in zip(a,b))}, only v2 {sum(p and not q for p,q in zip(a,b))}, only {name.split()[0]} {sum(q and not p for p,q in zip(a,b))}, both fail {sum(not p and not q for p,q in zip(a,b))}")
PY
