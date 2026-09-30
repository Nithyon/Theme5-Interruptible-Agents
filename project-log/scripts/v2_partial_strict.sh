#!/usr/bin/env bash
# Exact-match scoring of the 34 recordings that run v2 finished before it was stopped.
# Reads result files only; writes to /tmp/demo (not to any run folder). No model, no API, no agent.
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
mkdir -p /tmp/demo
nice -n 15 python evaluate_pass_rate.py --benchmark benchmark_data_v2.json --results-dir fdb_v3_data_released \
  --provider gate_gemini38_v2 --output /tmp/demo/v2_partial_strict.json > /tmp/demo/v2_partial_strict.log 2>&1
echo "scorer exit=$?"
python - <<'PY'
import json, glob, os
R = "/mnt/d/Theme5-Interruptible-Agents/project-log/runs"
def flags(path):
    r = json.load(open(path))
    return {x["scenario_id"]: x for x in r["scenario_results"]}, r
v2, rep = flags("/tmp/demo/v2_partial_strict.json")
print("v2 partial report: total_scenarios", rep.get("total_scenarios"), "passed", rep.get("passed"), "failed", rep.get("failed"))
print("failure breakdown:", rep.get("failure_breakdown"))
statuses = {}
for x in v2.values():
    k = x.get("failure_type") or x.get("status") or ("pass" if x["passed"] else "fail")
    statuses[k] = statuses.get(k, 0) + 1
print("per-item categories:", statuses)
print("item keys:", sorted(next(iter(v2.values())).keys()))
PY
