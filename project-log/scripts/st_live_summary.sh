#!/usr/bin/env bash
# Read-only: what has Smart Turn done so far in the run in progress? (reads the gate's decision log)
date -u '+now %H:%M UTC'
python3 - <<'PY'
import json, os, statistics as st
D = os.path.expanduser("~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released")
n = sum(os.path.exists(os.path.join(D, f, "result_gate_gemini38_v3st.json")) for f in os.listdir(D))
print("v3st results so far:", n, "/100")
f = "/tmp/gate_events.log"
rooms = [json.loads(l) for l in open(f)] if os.path.exists(f) else []
ps, holds, ext = [], [], 0
for r in rooms:
    ev = r["events"]; last_p = None
    for e in ev:
        if e["kind"] == "smart_turn": last_p = e.get("p_complete"); ps.append(last_p)
        if e["kind"] == "execute":
            holds.append(e.get("held_s"))
            if last_p is not None and last_p < 0.5: ext += 1
real = [p for p in ps if p is not None]
print(f"rooms logged: {len(rooms)} | smart turn verdicts: {len(ps)} (failed: {len(ps)-len(real)})")
if real:
    print(f"  said 'finished' (p>=0.5): {sum(p >= 0.5 for p in real)} | said 'not finished' (p<0.5): {sum(p < 0.5 for p in real)} | median p {st.median(real):.2f}")
    print("  verdicts:", [round(p, 2) for p in real])
if holds: print(f"executed calls: {len(holds)} | median hold {st.median(holds):.2f}s | max {max(holds):.2f}s | executed after a 'not finished' verdict: {ext}")
sup = sum(sum(e["kind"] == "superseded" for e in r["events"]) for r in rooms); ret = sum(sum(e["kind"] == "cancelled" for e in r["events"]) for r in rooms)
print("superseded calls:", sup, "| withdrawn calls:", ret)
PY
f=/tmp/gate_stats.log; [ -f $f ] && python3 -c "
import json
rows=[json.loads(l) for l in open('$f')]
st=[r.get('smart_turn') for r in rows if r.get('smart_turn')]
print('smart turn calls', sum(s['calls'] for s in st), 'errors', sum(s['errors'] for s in st), 'avg ms', round(sum(s['ms_total'] for s in st)/max(1,sum(s['calls'] for s in st))))"
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/silent_rooms.sh | tail -2
