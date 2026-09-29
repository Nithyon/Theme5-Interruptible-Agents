"""Scenarios that passed in run A but failed in run B (judged), with failure KIND only and
our agent's own calls in both runs. Never prints expected values."""
import glob, json, sys
DOM = sys.argv[1]
RA = ("/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-29_full_gemini3_8/gemini3_8_pass_rate_report_geminijudge.json", "gemini3_8")
RB = ("/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-29_full_gate_gemini38_final/gate_gemini38_final_pass_rate_report_geminijudge.json", "gate_gemini38_final")
def load(p): return {s["scenario_id"]: s for s in json.load(open(p))["scenario_results"]}
a, b = load(RA[0]), load(RB[0])
def kind(s):
    r = (s.get("failure_reason") or "").lower()
    return ("missing+extra" if "missing" in r and "unexpected" in r else "extra call" if "unexpected" in r
            else "missing call" if "missing" in r else "wrong args" if "argument" in r else "other")
def calls(folder_glob, prov):
    out = []
    for f in sorted(glob.glob(folder_glob + f"/result_{prov}.json")):
        x = json.load(open(f)); out.append([(c.get("function"), c.get("arguments") or c.get("args")) for c in x.get("actual_tool_calls", [])])
    return out
D = "/home/saini/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released"
def sel(k):
    if DOM.startswith("feature:"):
        return DOM.split(":", 1)[1].upper() in json.dumps(a[k].get("disfluency", "")).upper()
    return k.startswith(DOM)
lost = [k for k in a if sel(k) and a[k]["passed"] and not b.get(k, {}).get("passed")]
won = [k for k in a if sel(k) and not a[k]["passed"] and b.get(k, {}).get("passed")]
print(f"{DOM}: lost {len(lost)}, gained {len(won)}")
for k in lost:
    print(f"\n== {k}  now fails: {kind(b[k])}")
    print("   baseline calls:", calls(f"{D}/{k}_*", RA[1]))
    print("   final calls:   ", calls(f"{D}/{k}_*", RB[1]))
