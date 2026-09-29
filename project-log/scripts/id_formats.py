"""How our agent formatted identifier arguments in each run (our outputs only)."""
import collections, glob, json, re, sys
D = "/home/saini/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released"
for prov in sys.argv[1:]:
    c = collections.Counter(); ex = collections.defaultdict(list)
    for f in glob.glob(f"{D}/*/result_{prov}.json"):
        for call in json.load(open(f)).get("actual_tool_calls", []):
            for k, v in (call.get("arguments") or call.get("args") or {}).items():
                if not (k.endswith("_id") or k.endswith("_number")) or not isinstance(v, str):
                    continue
                c["ids"] += 1
                for tag, bad in (("hyphen", "-" in v), ("space", " " in v), ("lowercase", v != v.upper()),
                                 ("dot/#", bool(re.search(r"[.#]", v)))):
                    if bad:
                        c[tag] += 1; ex[tag].append(v)
    print(prov, dict(c), {t: ex[t][:4] for t in ex})
