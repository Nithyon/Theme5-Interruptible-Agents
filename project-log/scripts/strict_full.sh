#!/usr/bin/env bash
# Exact-match score of a finished run on all its recordings. Usage: strict_full.sh <provider>
# Reads result files; writes only to /tmp/demo. No model, no API, no agent.
P=${1:?provider}
source ~/theme5/fdb-env/bin/activate; cd ~/theme5/Full-Duplex-Bench/v3; mkdir -p /tmp/demo
nice -n 15 python evaluate_pass_rate.py --benchmark benchmark_data_v2.json --results-dir fdb_v3_data_released --provider "$P" --output /tmp/demo/full_$P.json > /tmp/demo/full_$P.log 2>&1
python - "$P" <<'PY'
import json, sys
r = json.load(open(f"/tmp/demo/full_{sys.argv[1]}.json"))
dom = {}
for x in r["scenario_results"]:
    d = dom.setdefault(x["domain"], [0, 0]); d[1] += 1; d[0] += bool(x["passed"])
print(f"{sys.argv[1]}: strict {r.get('passed')}/{r.get('total_scenarios')} |", " ".join(f"{k.split('_')[0]} {v[0]}/{v[1]}" for k, v in sorted(dom.items())), "|", r.get("failure_breakdown"))
PY
