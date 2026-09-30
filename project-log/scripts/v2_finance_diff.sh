#!/usr/bin/env bash
# For the finance recordings v2 finished: our own tool calls in v2 vs yesterday's pipeline vs stock.
# Reads only our agents' outputs (result_*.json), never the benchmark's expected answers.
python3 - <<'PY'
import json, os
D = os.path.expanduser("~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released")
def load(f, p):
    try: return json.load(open(os.path.join(D, f, f"result_{p}.json")))
    except Exception: return None
def calls(r):
    out = []
    for c in (r or {}).get("actual_tool_calls") or []:
        if isinstance(c, dict):
            name = c.get("name") or c.get("tool") or c.get("function") or "?"
            args = c.get("arguments") or c.get("args") or c.get("parameters") or {}
            out.append(f"{name}({json.dumps(args, sort_keys=True)})")
        else: out.append(str(c))
    return out
n = 0
for f in sorted(os.listdir(D)):
    r2 = load(f, "gate_gemini38_v2")
    if not r2 or "financ" not in str(r2.get("category", "")).lower() + str(r2.get("example_id", "")).lower(): continue
    n += 1
    a, b, c = calls(r2), calls(load(f, "gate_gemini38_final")), calls(load(f, "gemini3_8"))
    print(f"\n[{f[:22]}] example={r2.get('example_id')} status={r2.get('status')} | v2 == yesterday's pipeline: {a == b} | v2 == stock: {a == c}")
    print("   v2       :", a); print("   pipeline :", b); print("   stock    :", c)
print("\nfinance recordings with a v2 result:", n)
PY
