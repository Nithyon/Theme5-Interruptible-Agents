"""Decision-level evaluation: rules vs Jev on our own dev scenarios (no audio, no LiveKit).

1. Turn state. For each utterance with pause markers, every prefix cut at a "[pause Ns]"
   marker is labelled "continuing" (the user goes on speaking) and the full utterance is
   labelled "complete". Rules = the gate's hesitant/dangling-word check; Jev = turn_state.
2. Follow-up kind. Scenarios whose must_not_call names the same tool as an expected call are
   corrections; scenarios with two expected calls to the same tool are additions. The text
   between is taken after the correction/addition cue. Rules = classify_followup; Jev = followup.

Run: ~/theme5/fdb-env/bin/python devset/eval_decisions.py   (needs TYPESAFE_API_KEY in .env.local)
"""
import asyncio
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "fdb_agent"))
load_dotenv(Path.home() / "theme5/Full-Duplex-Bench/v3/.env.local")
os.environ.setdefault("GATE_DANGLING", "1")
import gate                                            # noqa: E402
import jev                                             # noqa: E402

jev.TIMEOUT_S = 5.0
PAUSE = re.compile(r"\s*\[pause [\d.]+s\]\s*")
CUES = re.compile(r"\b(no wait|no,|no |actually|sorry|wait|i meant|i mean|make that|make it|instead|hold on|and also|and the|also|too)\b", re.I)


def turn_items(rows):
    items = []
    for r in rows:
        parts = PAUSE.split(r["utterance"])
        if len(parts) < 2:
            continue
        for i in range(1, len(parts)):
            items.append((" ".join(parts[:i]).strip(), "continuing", r["id"]))
        items.append((PAUSE.sub(" ", r["utterance"]).strip(), "complete", r["id"]))
    return items


def followup_items(rows):
    items = []
    for r in rows:
        calls = r["expected_calls"]; mnc = r.get("must_not_call")
        text = PAUSE.sub(" ", r["utterance"])
        m = CUES.search(text)
        said = text[m.start():] if m else text[len(text) // 2:]
        if mnc and any(c["name"] == mnc["name"] for c in calls):
            new = next(c for c in calls if c["name"] == mnc["name"])
            items.append(({"tool": mnc["name"], "args": mnc["args"]},
                          {"tool": new["name"], "args": new["args"]}, said, "correction", r["id"]))
        names = [c["name"] for c in calls]
        for n in set(names):
            same = [c for c in calls if c["name"] == n]
            if len(same) >= 2 and not mnc:
                items.append(({"tool": n, "args": same[0]["args"]}, {"tool": n, "args": same[1]["args"]},
                              said, "addition", r["id"]))
    return items


def rules_turn(text):
    return "continuing" if gate.ends_hesitantly(text) else "complete"


def rules_followup(said):
    k = gate.classify_followup(said)
    return {"correction": "correction", "addition": "addition"}.get(k, "correction")  # unclear→replace


async def main():
    rows = [json.loads(l) for l in open(HERE / "scenarios.jsonl") if l.strip()]
    judge = jev.make_judge()
    if judge is None:
        sys.exit("Jev disabled: TYPESAFE_API_KEY missing")
    report = {}

    t_items = turn_items(rows)
    res = {"rules": {"ok": 0}, "jev": {"ok": 0, "none": 0}}
    cm = {"rules": {}, "jev": {}}
    per_item = []
    for text, label, sid in t_items:
        r = rules_turn(text)
        res["rules"]["ok"] += r == label
        cm["rules"][(label, r)] = cm["rules"].get((label, r), 0) + 1
        p = await judge.turn_state(text)
        j = max(p, key=p.get) if p else None
        if j is None:
            res["jev"]["none"] += 1
        res["jev"]["ok"] += j == label
        cm["jev"][(label, j)] = cm["jev"].get((label, j), 0) + 1
        per_item.append({"id": sid, "label": label, "rules": r, "jev": j,
                         "p_cont": round((p or {}).get("continuing", 0), 3)})
    n = len(t_items)
    # combined decider: hold if EITHER the rules or Jev says the user is continuing
    comb = [("continuing" if (x["rules"] == "continuing" or x["jev"] == "continuing") else "complete") for x in per_item]
    comb_ok = sum(c == x["label"] for c, x in zip(comb, per_item))
    comb_catch = sum(c == "continuing" and x["label"] == "continuing" for c, x in zip(comb, per_item))
    comb_false = sum(c == "continuing" and x["label"] == "complete" for c, x in zip(comb, per_item))
    cont = sum(1 for _, l, _ in t_items if l == "continuing")
    def recall(who):
        return sum(v for (l, g), v in cm[who].items() if l == "continuing" and g == "continuing") / max(cont, 1)
    report["turn_state"] = {"items": n, "continuing_items": cont,
                            "rules_accuracy": round(res["rules"]["ok"] / n, 3),
                            "jev_accuracy": round(res["jev"]["ok"] / n, 3),
                            "rules_catch_pause": round(recall("rules"), 3),
                            "jev_catch_pause": round(recall("jev"), 3),
                            "jev_no_answer": res["jev"]["none"],
                            "either_accuracy": round(comb_ok / n, 3),
                            "either_catch_pause": round(comb_catch / max(sum(1 for x in per_item if x["label"] == "continuing"), 1), 3),
                            "either_false_continuing": comb_false,
                            "per_item": per_item,
                            "confusion": {w: {f"{a}->{b}": v for (a, b), v in cm[w].items()} for w in cm}}

    f_items = followup_items(rows)
    ok = {"rules": 0, "jev": 0}; none = 0; by = {"correction": [0, 0, 0], "addition": [0, 0, 0]}
    for old, new, said, label, sid in f_items:
        r = rules_followup(said)
        p = await judge.followup(old, new, said)
        j = max(p, key=p.get) if p else None
        none += j is None
        ok["rules"] += r == label; ok["jev"] += j == label
        by[label][0] += 1; by[label][1] += r == label; by[label][2] += j == label
    m = len(f_items)
    report["followup"] = {"items": m, "rules_accuracy": round(ok["rules"] / max(m, 1), 3),
                          "jev_accuracy": round(ok["jev"] / max(m, 1), 3), "jev_no_answer": none,
                          "by_label [n, rules_ok, jev_ok]": by}
    report["jev_stats"] = judge.stats
    print(json.dumps(report, indent=1))
    out = HERE.parent / "project-log/runs/2026-09-29_decision_eval.json"
    out.write_text(json.dumps(report, indent=1))
    print("saved", out)


asyncio.run(main())
