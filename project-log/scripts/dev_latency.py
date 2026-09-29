import glob, json, statistics, sys
for L in sys.argv[1:]:
    fs = glob.glob(f"/mnt/d/Theme5-Interruptible-Agents/devset/audio/*/result_dev_gate_gemini38_{L}.json")
    lat = [json.load(open(f)).get("perceived_total_latency") for f in fs]
    lat = [x for x in lat if isinstance(x, (int, float)) and x > 0]
    p = [f for f in fs if "/p" in f.split("audio/")[1][:2]]
    print(L, "results:", len(fs), "(p-items:", len(p), ") | perceived latency median", round(statistics.median(lat), 2) if lat else None, "s, n", len(lat))
