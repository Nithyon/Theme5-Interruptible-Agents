"""Score our agent's runs against devset/scenarios.jsonl (never against FDB-v3 test items).

Reads devset/audio/<scenario_id>_<hex>/result_<provider>.json (written by the benchmark's
own run_tool_benchmark_all_released.py --root_dir devset/audio) and scores each render
against its scenario line in devset/scenarios.jsonl:

  - Strict pass: the multiset of called tool names must exactly equal the expected set (no
    missing, no extra — same rule as evaluate_pass_rate.py's tool_selection check, read
    directly from that file to confirm), and every expected call's arguments must match
    after light normalization (case, surrounding whitespace, underscores-to-spaces — the
    same normalization evaluate_pass_rate.py's exact_match_args applies).
  - must_not_call hit rate: for scenarios with a must_not_call, whether that exact stale
    call (name + normalized args) shows up anywhere in actual_tool_calls. This should be
    as close to 0% as possible — a hit means the gate let a pre-correction call through.

WRITE-ONLY DRAFT in this session: not run here (no result_*.json exists yet — the gate run
was using the GPU/CPU and devset/audio/ doesn't exist until make_audio.py has been run).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
SCENARIOS_PATH = HERE / "scenarios.jsonl"

_NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
}


def _norm_value(v: Any) -> Any:
    """Same light normalization evaluate_pass_rate.py's exact_match_args applies to
    strings: lowercase, strip, underscores to spaces. Also spells out small number words,
    since a realtime model may say "two" where the expected value is 2."""
    if isinstance(v, str):
        s = v.strip().lower().replace("_", " ")
        return _NUMBER_WORDS.get(s, s)
    return v


def _norm_args(args: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _norm_value(v) for k, v in args.items() if v is not None}


def load_scenarios() -> Dict[str, dict]:
    scenarios = {}
    with open(SCENARIOS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                d = json.loads(line)
                scenarios[d["id"]] = d
    return scenarios


def find_result_files(devset_dir: Path, provider: str) -> List[Path]:
    return sorted(devset_dir.glob(f"*/result_{provider}.json"))


def scenario_id_from_folder(folder_name: str) -> str:
    # folder is "<scenario_id>_<24-hex>"; scenario ids are "s" + digits (e.g. s07, s41)
    m = re.match(r"^([sp]\d+)_[0-9a-f]{24}$", folder_name)   # s = ours, p = Lohit's pause set
    return m.group(1) if m else folder_name


def score_one(scenario: dict, actual_calls: List[dict]) -> Dict[str, Any]:
    expected = scenario["expected_calls"]
    expected_names = [c["name"] for c in expected]
    actual_names = [c.get("function", c.get("name")) for c in actual_calls]

    exp_remaining = list(expected_names)
    act_remaining = list(actual_names)
    for name in list(exp_remaining):
        if name in act_remaining:
            exp_remaining.remove(name)
            act_remaining.remove(name)
    tool_selection_ok = not exp_remaining and not act_remaining

    args_ok = True
    if tool_selection_ok:
        actual_by_func: Dict[str, List[dict]] = {}
        for ac in actual_calls:
            actual_by_func.setdefault(ac.get("function", ac.get("name")), []).append(ac)
        for ec in expected:
            calls = actual_by_func.get(ec["name"], [])
            if not calls:
                args_ok = False
                break
            actual_call = calls.pop(0)
            if _norm_args(actual_call.get("args", {})) != _norm_args(ec["args"]):
                args_ok = False
                break

    strict_pass = tool_selection_ok and args_ok

    must_not_call_hit = False
    mnc = scenario.get("must_not_call")
    if mnc:
        target = (mnc["name"], json.dumps(_norm_args(mnc["args"]), sort_keys=True))
        for ac in actual_calls:
            key = (ac.get("function", ac.get("name")), json.dumps(_norm_args(ac.get("args", {})), sort_keys=True))
            if key == target:
                must_not_call_hit = True
                break

    return {
        "strict_pass": strict_pass,
        "tool_selection_ok": tool_selection_ok,
        "args_ok": args_ok if tool_selection_ok else None,
        "must_not_call_hit": must_not_call_hit if mnc else None,
        "missing_tools": exp_remaining,
        "extra_tools": act_remaining,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--provider", required=True)
    ap.add_argument("--devset-dir", default=str(HERE / "audio"))
    args = ap.parse_args()

    devset_dir = Path(args.devset_dir)
    scenarios = load_scenarios()
    result_files = find_result_files(devset_dir, args.provider)

    if not result_files:
        print(f"no result_{args.provider}.json files found under {devset_dir} "
              f"(run devset/run_dev.sh first)")
        return

    rows = []
    for rf in result_files:
        folder = rf.parent.name
        sid = scenario_id_from_folder(folder)
        scenario = scenarios.get(sid)
        if scenario is None:
            print(f"  ⚠️  {folder}: scenario id {sid!r} not found in scenarios.jsonl, skipping")
            continue
        with open(rf, "r", encoding="utf-8") as f:
            result = json.load(f)
        if result.get("status") != "completed":
            rows.append({"folder": folder, "id": sid, "status": result.get("status", "unknown"),
                        "strict_pass": False, "must_not_call_hit": None})
            continue
        score = score_one(scenario, result.get("actual_tool_calls", []))
        rows.append({"folder": folder, "id": sid, "status": "completed", **score})

    total = len(rows)
    passed = sum(1 for r in rows if r["strict_pass"])
    mnc_applicable = [r for r in rows if r.get("must_not_call_hit") is not None]
    mnc_hits = sum(1 for r in mnc_applicable if r["must_not_call_hit"])

    print(f"{'folder':<40} {'scenario':<6} {'status':<12} {'pass':<6} {'must_not_call_hit'}")
    for r in rows:
        print(f"{r['folder']:<40} {r['id']:<6} {r['status']:<12} "
              f"{'PASS' if r.get('strict_pass') else 'fail':<6} "
              f"{r.get('must_not_call_hit', '-')}")

    print("\n--- summary ---")
    print(f"strict pass: {passed}/{total} ({passed / total:.1%})" if total else "no scored rows")
    if mnc_applicable:
        print(f"must_not_call hits: {mnc_hits}/{len(mnc_applicable)} "
              f"({mnc_hits / len(mnc_applicable):.1%}) — lower is better, 0% is the goal")
    by_domain: Dict[str, List[bool]] = {}
    for r in rows:
        sid = r["id"]
        scenario = scenarios.get(sid)
        if scenario:
            by_domain.setdefault(scenario["domain"], []).append(bool(r.get("strict_pass")))
    for domain, results in sorted(by_domain.items()):
        print(f"  {domain}: {sum(results)}/{len(results)} ({sum(results) / len(results):.1%})")


if __name__ == "__main__":
    main()
