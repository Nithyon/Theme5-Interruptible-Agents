"""Our outputs for runs with no tool call: status, how much the agent said, keys present."""
import json, pathlib, sys
prov = sys.argv[1]
D = pathlib.Path.home() / "theme5/Full-Duplex-Bench/v3/fdb_v3_data_released"
for f in sorted(D.glob(f"*/result_{prov}.json")):
    x = json.load(open(f))
    if x.get("actual_tool_calls"):
        continue
    t = x.get("transcript") or ""
    print(f.parent.name[:22], "| status:", x.get("status"), "| agent said:", len(t), "chars",
          "| latency:", x.get("perceived_total_latency"), "| wav bytes:",
          (f.parent / f"output_{prov}.wav").stat().st_size if (f.parent / f"output_{prov}.wav").exists() else None)
    print("   agent words:", t[:160].replace("\n", " "))
