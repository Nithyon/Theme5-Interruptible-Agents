#!/usr/bin/env bash
# Read-only: reply-speed medians straight from the per-recording result files, same fields for every run.
python3 - <<'PY'
import json, os, statistics as st
D = os.path.expanduser("~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released")
runs = [("stock agent", "gemini3_8"), ("29 Sep pipeline", "gate_gemini38_final"), ("today, Smart Turn ON", "gate_gemini38_v3st"), ("today, Smart Turn OFF", "gate_gemini38_v2b")]
for label, prov in runs:
    perc, first, tool = [], [], []
    for f in os.listdir(D):
        p = os.path.join(D, f, f"result_{prov}.json")
        if not os.path.exists(p): continue
        r = json.load(open(p))
        if isinstance(r.get("perceived_total_latency"), (int, float)): perc.append(r["perceived_total_latency"])
        ue, a = r.get("user_speech_end_rel"), r.get("audio_agent_speech_start")
        if isinstance(ue, (int, float)) and isinstance(a, (int, float)) and a > ue: first.append(a - ue)
        calls = r.get("actual_tool_calls") or []
        if calls and isinstance(ue, (int, float)) and isinstance(calls[0].get("timestamp_start"), (int, float)) and calls[0]["timestamp_start"] > ue:
            tool.append(calls[0]["timestamp_start"] - ue)
    med = lambda x: f"{st.median(x):.2f} s (n={len(x)})" if x else "n/a"
    print(f"{label:24} perceived latency median {med(perc)} | speech start after user stops: {med(first)} | first tool call after user stops: {med(tool)}")
PY
