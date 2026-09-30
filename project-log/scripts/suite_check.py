"""Recount a fallback-suite folder from its per-run result files and print it next to summary.json."""
import glob, json, os, sys

d = sys.argv[1]
s = json.load(open(os.path.join(d, "summary.json"), encoding="utf-8"))
print("model", s["model"], "| machine", {k: s["machine"].get(k) for k in ("cpu", "ram_gb", "tokens_per_second", "loaded_gb", "on_gpu_gb")})
for name, v in s["sets"].items():
    for i, r in enumerate(v["runs"], 1):
        res = json.load(open(os.path.join(d, f"{name}_run{i}.json"), encoding="utf-8"))["results"]
        act = [x for x in res if x["expect_tool"]]; none = [x for x in res if not x["expect_tool"]]
        declined = sum(1 for x in act if x["got"] is not None and x["got"].get("tool") is None)
        print(f"{name} run{i}: recount right_tool {sum(x['tool_ok'] for x in act)}/{len(act)} fully {sum(x['args_ok'] for x in act)}/{len(act)}"
              f" stayed_out {sum(x['tool_ok'] for x in none)}/{len(none)} declined {declined} | summary says {r['right_tool']}/{r['should_act_n']}"
              f" {r['fully_correct']} {r['stayed_out_correctly']} median {r['latency_median_s']}")
    print(f"{name}: changed across runs {v['commands_with_different_outcome_across_runs']}")
