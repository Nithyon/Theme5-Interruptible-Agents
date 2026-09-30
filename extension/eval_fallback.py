"""Evaluate LocalFallback on extension/fallback_eval.jsonl (our own examples, no benchmark data).

Requires a running local Ollama server with the model pulled; see project-log/scripts/fallback_eval.sh.
Usage: python eval_fallback.py [--limit N] [--model NAME] [--mode tools|json] [--timeout S]
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import statistics
import time

from local_fallback import DEFAULT_MODEL, TOOL_SETS, LocalFallback

HERE = os.path.dirname(os.path.abspath(__file__))
SELF_CORRECT = re.compile(r"\b(no|sorry)\s*,", re.I)


def _eq(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) or isinstance(b, (int, float)):
        try:
            return float(a) == float(b)
        except (TypeError, ValueError):
            return False
    return str(a).strip().lower() == str(b).strip().lower()


def args_match(expect: dict, got: dict) -> bool:
    """Every expected key must be present and equal. Extra keys the model added are ignored."""
    return all(k in got and _eq(v, got[k]) for k, v in expect.items())


def pct(n, d):
    return None if d == 0 else round(100.0 * n / d, 1)


def p95(xs):
    s = sorted(xs)
    return s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))] if s else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--mode", default="tools", choices=["tools", "json"])
    ap.add_argument("--timeout", type=float, default=8.0)
    ap.add_argument("--data", default=os.path.join(HERE, "fallback_eval.jsonl"))
    a = ap.parse_args()

    rows = [json.loads(l) for l in open(a.data, encoding="utf-8") if l.strip()]
    if a.limit:
        rows = rows[: a.limit]
    fb = LocalFallback(model=a.model, timeout=a.timeout, mode=a.mode)

    results, lat = [], []
    for r in rows:
        t0 = time.perf_counter()
        d = fb.decide(r["text"], TOOL_SETS[r["pack"]])
        dt = time.perf_counter() - t0
        lat.append(dt)
        got_tool = d.get("tool") if d else None
        exp = r["expect_tool"]
        tool_ok = (d is not None) and got_tool == exp
        args_ok = tool_ok and (exp is None or args_match(r["expect_args"], d.get("args", {})))
        results.append({**r, "got": d, "tool_ok": tool_ok, "args_ok": args_ok,
                        "self_correct": bool(SELF_CORRECT.search(r["text"])), "latency_s": round(dt, 3)})
        print(f"{'OK ' if args_ok else ('T  ' if tool_ok else 'X  ')} {dt:5.2f}s  {r['text']!r} -> {d}")

    n = len(results)
    sc = [x for x in results if x["self_correct"]]
    expected_none = [x for x in results if x["expect_tool"] is None]
    predicted_none = [x for x in results if x["got"] is not None and x["got"].get("tool") is None]
    tp_none = [x for x in predicted_none if x["expect_tool"] is None]
    summary = {
        "model": a.model, "mode": a.mode, "n": n, "timeout_s": a.timeout,
        "errors_or_timeouts": sum(x["got"] is None for x in results),
        "tool_selection_acc_pct": pct(sum(x["tool_ok"] for x in results), n),
        "exact_args_acc_pct": pct(sum(x["args_ok"] for x in results), n),
        "self_correction_n": len(sc),
        "self_correction_exact_acc_pct": pct(sum(x["args_ok"] for x in sc), len(sc)),
        "no_tool_precision_pct": pct(len(tp_none), len(predicted_none)),
        "no_tool_recall_pct": pct(len(tp_none), len(expected_none)),
        "latency_mean_s": round(statistics.mean(lat), 3) if lat else None,
        "latency_median_s": round(statistics.median(lat), 3) if lat else None,
        "latency_p95_s": round(p95(lat), 3) if lat else None,
    }
    print("\n=== SUMMARY ===")
    for k, v in summary.items():
        print(f"{k}: {v}")

    outdir = os.path.join(HERE, "..", "project-log", "runs")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.normpath(os.path.join(outdir, f"{datetime.date.today().isoformat()}_local_fallback_eval.json"))
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)
    print("report:", path)


if __name__ == "__main__":
    main()
