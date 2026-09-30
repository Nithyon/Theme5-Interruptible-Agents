#!/usr/bin/env bash
# Recount both interruption-set folders from their raw files, and list the cancelled actions that ran.
cd /mnt/d/Theme5-Interruptible-Agents
for d in project-log/runs/*_interrupt; do
  echo "== $d"
  python3 project-log/scripts/suite_check.py "$d"
  python3 - "$d" <<'PY'
import json, sys, os, collections
d = sys.argv[1]
res = json.load(open(os.path.join(d, "interrupt_run1.json")))["results"]
k = collections.OrderedDict()
for x in res:
    k.setdefault(x["kind"], [0, 0]); k[x["kind"]][1] += 1; k[x["kind"]][0] += x["args_ok"]
print("  by kind:", ", ".join(f"{a} {b[0]}/{b[1]}" for a, b in k.items()))
for x in res:
    if x["expect_tool"] is None and x["got"] and x["got"].get("tool"):
        print("  ACTED ON CANCELLED:", repr(x["text"]), "->", x["got"])
    if x["expect_tool"] and not x["args_ok"]:
        print("  MISS:", repr(x["text"]), "->", x["got"])
PY
done
