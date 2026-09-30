#!/usr/bin/env bash
# Keep the first in-car attempt, check the agent still imports and its tests pass, then run again.
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs
[ -d $R/$(date +%F)_ext_car_e2e ] && [ ! -d $R/$(date +%F)_ext_car_e2e_attempt1 ] && mv $R/$(date +%F)_ext_car_e2e $R/$(date +%F)_ext_car_e2e_attempt1
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/ext_check.sh
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/ext_car_full.sh
python3 - <<'PY'
import json
r = json.load(open("/mnt/d/Theme5-Interruptible-Agents/project-log/runs/" + __import__("datetime").date.today().isoformat() + "_ext_car_e2e/result.json"))
print("FULL TRANSCRIPT:", r.get("transcript"))
PY
