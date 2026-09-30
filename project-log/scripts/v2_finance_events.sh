#!/usr/bin/env bash
# What did the Commit Harness decide in the five finance rooms of run v2? (our own decision log)
python3 - <<'PY'
import json, os
D = os.path.expanduser("~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released")
R = "/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-30_full_gate_gemini38_v2"
ev = {}
for name in ("gate_events.log",):
    p = os.path.join(R, name)
    print(name, "exists:", os.path.exists(p), "| rooms logged:", sum(1 for _ in open(p)) if os.path.exists(p) else 0)
    if os.path.exists(p):
        for line in open(p):
            d = json.loads(line); ev[d["room"]] = d["events"]
for f in sorted(os.listdir(D)):
    rp = os.path.join(D, f, "result_gate_gemini38_v2.json")
    if not os.path.exists(rp) or not f.startswith("finance"): continue
    r = json.load(open(rp)); room = r.get("room_name"); e = ev.get(room)
    print(f"\n[{f[:22]}] room={room} evaluated_at={r.get('evaluated_at')} inference_s={r.get('inference_time_s')} calls={len(r.get('actual_tool_calls') or [])}")
    print("   agent transcript (first 160):", repr((r.get("transcript") or "")[:160]))
    if e is None: print("   NO gate events logged for this room"); continue
    kinds = {}
    for x in e: kinds[x["kind"]] = kinds.get(x["kind"], 0) + 1
    print("   event counts:", kinds)
    t0 = e[0]["t"] if e else 0
    for x in e:
        if x["kind"] in ("proposed", "execute", "superseded", "cancelled", "retracted", "same_tool_again", "duplicate", "backchannel", "jev_turn", "turn_done") or (x["kind"] == "transcript"):
            d = {k: v for k, v in x.items() if k not in ("t", "kind")}
            print(f"     +{x['t']-t0:6.1f}s {x['kind']:12} {json.dumps(d)[:150]}")
PY
grep -c "AssignmentTimeoutError\|job crashed" /mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-30_full_gate_gemini38_v2/agent.log
