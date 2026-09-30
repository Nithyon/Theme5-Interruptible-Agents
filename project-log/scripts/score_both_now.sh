#!/usr/bin/env bash
# Read-only interim scoring of the two live runs on exactly the same recordings (exact-match scorer,
# no model, no API, no agent). Writes only under /tmp/demo. Prints pass counts, never expected answers.
source ~/theme5/fdb-env/bin/activate
V3=~/theme5/Full-Duplex-Bench/v3; D=$V3/fdb_v3_data_released; C=/tmp/demo/common
rm -rf $C; mkdir -p $C
n3=0; nb=0
for f in $D/*/; do
  b=$(basename $f); a=0; c=0
  [ -f $f/result_gate_gemini38_v3st.json ] && { a=1; n3=$((n3+1)); }
  [ -f $f/result_gate_gemini38_v2b.json ] && { c=1; nb=$((nb+1)); }
  if [ $a = 1 ] && [ $c = 1 ]; then
    mkdir -p "$C/$b"; cp "$f"/metadata.json "$C/$b/" 2>/dev/null
    for p in gate_gemini38_v3st gate_gemini38_v2b gemini3_8 gate_gemini38_final; do cp "$f/result_$p.json" "$C/$b/" 2>/dev/null; done
  fi
done
k=$(ls $C | wc -l)
date -u '+%H:%M UTC'; echo "finished: Smart Turn ON (v3st) $n3/100 | Smart Turn OFF (v2b) $nb/100 | recordings finished by both: $k"
[ "$k" -eq 0 ] && exit 0
cd $V3
for p in gate_gemini38_v3st gate_gemini38_v2b gemini3_8 gate_gemini38_final; do
  nice -n 15 python evaluate_pass_rate.py --benchmark benchmark_data_v2.json --results-dir $C --provider $p --output /tmp/demo/common_$p.json > /tmp/demo/common_$p.log 2>&1 || echo "scorer failed for $p"
done
python - <<'PY'
import json, os
def rep(p):
    try: return json.load(open(f"/tmp/demo/common_{p}.json"))
    except Exception: return None
names = {"gate_gemini38_v3st": "Smart Turn ON  (v3st)", "gate_gemini38_v2b": "Smart Turn OFF (v2b) ", "gemini3_8": "stock agent (yesterday)", "gate_gemini38_final": "pipeline (yesterday)  "}
for p, label in names.items():
    r = rep(p)
    if not r: print(label, ": no report"); continue
    dom = {}
    for x in r["scenario_results"]:
        d = dom.setdefault(x["domain"][:9], [0, 0]); d[1] += 1; d[0] += bool(x["passed"])
    print(f"{label}: strict {r.get('passed')}/{r.get('total_scenarios')} | " + " ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(dom.items())) + f" | {r.get('failure_breakdown')}")
PY
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/silent_rooms.sh | grep 'v3st:\|v2b:'
echo "load: $(cut -d' ' -f1-3 /proc/loadavg)"
