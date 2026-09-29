"""Score an agent on every scenario JSON in one or more directories.

    py -3.12 tests/run_dir.py generated/si generated/ut --time-scale 4
"""

from __future__ import annotations
import argparse
import asyncio
import glob
import importlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from harness.runner import EvaluationHarness  # noqa: E402
from harness.scorer import score_scenario  # noqa: E402


def load_agent(spec: str):
    mod, cls = spec.split(":")
    return getattr(importlib.import_module(mod), cls)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--agent", default="agent.agent:ParticipantAgent")
    ap.add_argument("--time-scale", type=float, default=4.0)
    args = ap.parse_args()
    cls = load_agent(args.agent)
    paths = sorted(p for d in args.dirs for p in glob.glob(os.path.join(d, "*.json")))
    totals = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            scenario = json.load(f)
        harness = EvaluationHarness(scenario, cls, time_scale=args.time_scale, verbose=False)
        trace = asyncio.run(harness.run())
        res = score_scenario(scenario, trace)
        totals.append(res["total"])
        crashes = [e for e in trace if e["kind"] in ("agent_crash", "protocol_error")]
        flag = f"  <-- {crashes[0]}" if crashes else ""
        low = ""
        if res["total"] < 100:
            misses = []
            for cat, b in res.get("breakdown", {}).items():
                if b["fraction"] < 1:
                    d = b["detail"]
                    why = [c["id"] for c in d.get("checkpoints", []) if not c["passed"]]
                    why += [c["check"] for c in d.get("checks", []) if not c["passed"]]
                    why += [f"#{r['event_index']}={r['delta_ms']}ms" for r in d.get("responses", [])
                            if r["fraction"] < 1]
                    why += [n for n in d.get("notes", []) if n != "clean"]
                    misses.append(f"{cat} x{b['fraction']} {why}")
            low = "  [" + "; ".join(misses) + "]"
        print(f"{res['total']:6.1f}  {os.path.basename(p)}{low}{flag}")
    if totals:
        print(f"MEAN {sum(totals) / len(totals):.1f} over {len(totals)} scenario(s)")


if __name__ == "__main__":
    main()
