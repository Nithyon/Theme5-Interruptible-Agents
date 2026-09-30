"""Print the headline numbers of each local-fallback result file so they can be checked against the write-up."""
import glob, json, os, statistics, sys

root = sys.argv[1] if len(sys.argv) > 1 else "project-log/runs"
for p in sorted(glob.glob(os.path.join(root, "*local_fallback_eval*.json"))):
    d = json.load(open(p, encoding="utf-8"))
    print("==", os.path.basename(p))
    if isinstance(d, dict):
        print("   keys:", list(d.keys())[:12])
        for k, v in d.items():
            if not isinstance(v, (list, dict)):
                print("   ", k, "=", v)
            elif isinstance(v, dict) and len(v) < 15:
                print("   ", k, "=", v)
        rows = next((v for v in d.values() if isinstance(v, list) and v and isinstance(v[0], dict)), [])
    else:
        rows = d
    if rows:
        print("   rows:", len(rows), "row keys:", list(rows[0].keys()))
        for key in ("tool_ok", "tool_correct", "exact", "args_ok", "fully_correct"):
            if key in rows[0]:
                print("   ", key, sum(1 for r in rows if r.get(key)), "/", len(rows))
        lat = [r[k] for r in rows for k in ("latency_s", "seconds", "elapsed_s") if isinstance(r.get(k), (int, float))]
        if lat:
            print("    median latency", round(statistics.median(lat), 2))
