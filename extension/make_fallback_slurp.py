"""Build extension/fallback_eval_slurp.jsonl: 111 REAL user requests from the SLURP test set
(Bastianelli et al., EMNLP 2020; text licence CC BY 4.0), in the format eval_fallback.py reads.

Selection rule (fixed, no hand-picking): one shard of the SLURP test split, distinct sentences in
file order, until each quota is full.
  - 51 light-control requests (all the distinct ones in the shard) -> expect set_lights with the state the SLURP intent implies
    (lightoff -> off; lighton, lightup, lightdim -> on). Room and brightness are not scored:
    most requests name no room. The mapping from SLURP intent to our tool is OURS, not SLURP's.
  - 60 requests our home tools cannot serve (weather, music, email, news, facts, calendar)
    -> expect no tool. This is the check that the fallback does not act when it should not.

Run:  python extension/make_fallback_slurp.py ~/theme5/slurp/test-00000.parquet
"""
import json, os, sys

import pyarrow.parquet as pq

# the shard holds 25 distinct "off", 2 "on", 12 "dim" and 12 "brighter" sentences: 51 in all
LIGHTS = {"iot_hue_lightoff": ("off", 34), "iot_hue_lighton": ("on", 2),
          "iot_hue_lightdim": ("on", 12), "iot_hue_lightup": ("on", 12)}
NONE = {k: 10 for k in ("weather_query", "play_music", "email_query", "news_query", "qa_factoid", "calendar_set")}

t = pq.ParquetFile(sys.argv[1]).read(columns=["id", "transcript", "intent"]).to_pylist()
left = {**{k: v[1] for k, v in LIGHTS.items()}, **NONE}
seen, rows = set(), []
for r in t:
    k = r["intent"]
    if left.get(k, 0) <= 0 or r["id"] in seen or r["transcript"] in seen:
        continue
    seen.update((r["id"], r["transcript"])); left[k] -= 1
    lights = k in LIGHTS
    rows.append({"pack": "home", "text": r["transcript"],
                 "expect_tool": "set_lights" if lights else None,
                 "expect_args": {"state": LIGHTS[k][0]} if lights else {},
                 "slurp_id": r["id"], "slurp_intent": k})
rows.sort(key=lambda x: (x["expect_tool"] is None, x["slurp_intent"]))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fallback_eval_slurp.jsonl")
with open(out, "w", encoding="utf-8", newline="\n") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
print("wrote", out, len(rows), "rows; quotas not filled:", {k: v for k, v in left.items() if v})
