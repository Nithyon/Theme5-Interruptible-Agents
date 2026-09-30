"""Test suite for the local fallback: two command sets, several runs, and a record of the machine.

Sets (both small text files, nothing to download):
  own    extension/fallback_eval.jsonl        40 commands we wrote (car + home, 6 self-corrections)
  slurp  extension/fallback_eval_slurp.jsonl  111 real user requests from the SLURP test set:
                                              51 light-control (expect set_lights, right on/off)
                                              60 our tools cannot serve (expect no tool)
  interrupt  extension/fallback_eval_interrupt.jsonl  37 commands we wrote, the way people interrupt
                                              themselves: corrected values and places, a changed
                                              action, "never mind" (expect no tool), hesitations,
                                              words like "no rush" that are NOT corrections, double
                                              corrections. Scored per kind in summary.md.

Needs a running Ollama with the model pulled. Example:
    python extension/fallback_suite.py --model gemma4:26b-a4b-it-qat --runs 3 --timeout 30

Writes project-log/runs/<date>_fallback_suite_<model>/ : machine.json, <set>_run<N>.json (every
command with what the model returned), summary.json and summary.md (a table to paste).
At about 5 s per command, 3 runs of both sets take about 38 minutes; --runs 1 takes about 13.
"""
from __future__ import annotations

import argparse, datetime, json, os, platform, re, statistics, subprocess, time

import requests

from eval_fallback import SELF_CORRECT, args_match, p95
from local_fallback import OLLAMA_URL, TOOL_SETS, LocalFallback

HERE = os.path.dirname(os.path.abspath(__file__))
SETS = {"own": "fallback_eval.jsonl", "slurp": "fallback_eval_slurp.jsonl",
        "interrupt": "fallback_eval_interrupt.jsonl"}


def machine(url: str, model: str) -> dict:
    info = {"platform": platform.platform(), "processor": platform.processor(), "cpu_count": os.cpu_count(),
            "python": platform.python_version()}
    try:
        if os.path.exists("/proc/meminfo"):
            kb = int(re.search(r"MemTotal:\s+(\d+)", open("/proc/meminfo").read()).group(1))
            info["ram_gb"] = round(kb / 1e6, 1)
            m = re.search(r"model name\s*:\s*(.+)", open("/proc/cpuinfo").read())
            info["cpu"] = m.group(1).strip() if m else None
        elif platform.system() == "Darwin":
            info["ram_gb"] = round(int(subprocess.check_output(["sysctl", "-n", "hw.memsize"])) / 1e9, 1)
            info["cpu"] = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
    except Exception as e:  # machine details are a nicety; never fail the run over them
        info["machine_detail_error"] = type(e).__name__
    try:
        info["ollama_version"] = requests.get(url + "/api/version", timeout=10).json().get("version")
        d = requests.post(url + "/api/show", json={"model": model}, timeout=30).json().get("details", {})
        info["model_details"] = {k: d.get(k) for k in ("family", "parameter_size", "quantization_level")}
        r = requests.post(url + "/api/chat", timeout=300, json={
            "model": model, "stream": False, "think": False, "options": {"num_predict": 64},
            "messages": [{"role": "user", "content": "Count from one to twenty in words."}]}).json()
        if r.get("eval_duration"):
            info["tokens_per_second"] = round(r["eval_count"] / (r["eval_duration"] / 1e9), 1)
        ps = requests.get(url + "/api/ps", timeout=10).json().get("models", [])
        if ps:
            info["loaded_gb"] = round(ps[0].get("size", 0) / 1e9, 1)
            info["on_gpu_gb"] = round(ps[0].get("size_vram", 0) / 1e9, 1)
    except Exception as e:
        info["ollama_detail_error"] = f"{type(e).__name__}: {e}"
    return info


def run_set(fb: LocalFallback, rows: list) -> list:
    out = []
    for r in rows:
        t0 = time.perf_counter()
        d = fb.decide(r["text"], TOOL_SETS[r["pack"]])
        dt = time.perf_counter() - t0
        exp = r["expect_tool"]
        tool_ok = d is not None and d.get("tool") == exp
        args_ok = tool_ok and (exp is None or args_match(r["expect_args"], d.get("args", {})))
        out.append({**r, "got": d, "tool_ok": tool_ok, "args_ok": args_ok, "latency_s": round(dt, 3)})
        print(f"{'OK ' if args_ok else ('T  ' if tool_ok else 'X  ')} {dt:5.2f}s  {r['text']!r} -> {d}", flush=True)
    return out


def summarise(res: list) -> dict:
    act = [x for x in res if x["expect_tool"] is not None]
    none = [x for x in res if x["expect_tool"] is None]
    sc = [x for x in res if SELF_CORRECT.search(x["text"])]
    lat = [x["latency_s"] for x in res]
    return {"n": len(res), "right_tool": sum(x["tool_ok"] for x in act), "fully_correct": sum(x["args_ok"] for x in act),
            "should_act_n": len(act), "stayed_out_correctly": sum(x["tool_ok"] for x in none), "should_not_act_n": len(none),
            "acted_when_it_should_not": sum(1 for x in none if x["got"] and x["got"].get("tool")),
            "self_corrections_correct": sum(x["args_ok"] for x in sc), "self_corrections_n": len(sc),
            "no_answer": sum(x["got"] is None for x in res),
            "latency_median_s": round(statistics.median(lat), 2), "latency_p95_s": round(p95(lat), 2),
            "by_kind": {k: f"{sum(x['args_ok'] for x in res if x.get('kind') == k)}/{sum(1 for x in res if x.get('kind') == k)}"
                        for k in dict.fromkeys(x["kind"] for x in res if x.get("kind"))}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--sets", default="own,slurp,interrupt")
    ap.add_argument("--mode", default="tools", choices=["tools", "json"])
    ap.add_argument("--url", default=OLLAMA_URL)
    ap.add_argument("--limit", type=int, default=None, help="first N commands of each set (quick check)")
    a = ap.parse_args()

    tag = re.sub(r"[^A-Za-z0-9._-]+", "_", a.model)
    out = os.path.normpath(os.path.join(HERE, "..", "project-log", "runs",
                                        f"{datetime.date.today().isoformat()}_fallback_suite_{tag}"))
    os.makedirs(out, exist_ok=True)
    mach = machine(a.url, a.model)
    json.dump(mach, open(os.path.join(out, "machine.json"), "w", encoding="utf-8"), indent=2)
    print("machine:", json.dumps(mach))

    fb = LocalFallback(model=a.model, base_url=a.url, timeout=a.timeout, mode=a.mode)
    summary = {"model": a.model, "mode": a.mode, "timeout_s": a.timeout, "machine": mach, "sets": {}}
    for name in [s.strip() for s in a.sets.split(",") if s.strip()]:
        rows = [json.loads(l) for l in open(os.path.join(HERE, SETS[name]), encoding="utf-8") if l.strip()]
        rows = rows[: a.limit] if a.limit else rows
        runs, per_cmd = [], [[] for _ in rows]
        for i in range(1, a.runs + 1):
            print(f"\n=== {name} run {i}/{a.runs} ===", flush=True)
            res = run_set(fb, rows)
            s = summarise(res)
            json.dump({"summary": s, "results": res}, open(os.path.join(out, f"{name}_run{i}.json"), "w", encoding="utf-8"), indent=2)
            runs.append(s)
            for j, x in enumerate(res):
                per_cmd[j].append(x["args_ok"])
        summary["sets"][name] = {"runs": runs, "commands_with_different_outcome_across_runs": sum(len(set(p)) > 1 for p in per_cmd)}
    json.dump(summary, open(os.path.join(out, "summary.json"), "w", encoding="utf-8"), indent=2)

    md = [f"# Local fallback suite: {a.model}", "",
          f"Machine: {mach.get('cpu') or mach.get('processor')}, {mach.get('ram_gb', '?')} GB RAM, "
          f"{mach.get('on_gpu_gb', 0)} GB of the model on a GPU, Ollama {mach.get('ollama_version')}, "
          f"{mach.get('tokens_per_second', '?')} tokens/s. Timeout {a.timeout:.0f} s, mode {a.mode}.", "",
          "| Set | Run | Right tool | Fully correct | Stayed out when no tool fits | Self-corrections | No answer | Median time |",
          "|---|---|---|---|---|---|---|---|"]
    for name, v in summary["sets"].items():
        for i, s in enumerate(v["runs"], 1):
            md.append(f"| {name} | {i} | {s['right_tool']}/{s['should_act_n']} | {s['fully_correct']}/{s['should_act_n']} | "
                      f"{s['stayed_out_correctly']}/{s['should_not_act_n']} | {s['self_corrections_correct']}/{s['self_corrections_n']} | "
                      f"{s['no_answer']} | {s['latency_median_s']} s |")
        md.append(f"| {name} | | commands whose outcome changed between runs: {v['commands_with_different_outcome_across_runs']} | | | | | |")
    for name, v in summary["sets"].items():
        for i, s in enumerate(v["runs"], 1):
            if s["by_kind"]:
                md += ["", f"{name}, run {i}, fully correct by kind: " + ", ".join(f"{k} {n}" for k, n in s["by_kind"].items())]
    md += ["", "own = 40 commands we wrote. slurp = 111 real requests from the SLURP test set (51 light control, 60 that none of "
           "our tools can serve); the mapping from SLURP intent to our tool is ours. interrupt = 37 commands we wrote with "
           "mid-sentence corrections, cancellations, hesitations and false alarms. Typed text, no audio."]
    open(os.path.join(out, "summary.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n" + "\n".join(md)); print("\nfolder:", out)


if __name__ == "__main__":
    main()
