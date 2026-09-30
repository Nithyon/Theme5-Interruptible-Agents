#!/usr/bin/env bash
# Keep the second home attempt as a record and run the home assistant once more with the final fixes.
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs
[ -d $R/$(date +%F)_ext_home_e2e ] && [ ! -d $R/$(date +%F)_ext_home_e2e_attempt2 ] && mv $R/$(date +%F)_ext_home_e2e $R/$(date +%F)_ext_home_e2e_attempt2
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/ext_e2e.sh
python3 - <<'PY'
import json, datetime
r = json.load(open("/mnt/d/Theme5-Interruptible-Agents/project-log/runs/" + datetime.date.today().isoformat() + "_ext_home_e2e/result.json"))
print("FULL TRANSCRIPT:", r.get("transcript"))
PY
