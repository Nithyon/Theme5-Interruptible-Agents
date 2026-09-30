# Team handoff (submission day, 30 Sep 2026)

Deadline: **23:59 IST, 30 Sep 2026.** Aim to submit the form by **22:30 IST**.

## Who edits what
| Person | Edits | Output |
|---|---|---|
| README polisher | `README.md` (root) only | final README on GitHub |
| Deck maker | `project-log/SLIDES_OUTLINE.md` -> slides | deck, max 8 slides |
| Video | `project-log/VIDEO_SCRIPT.md` | 3-5 min video |
| Form filler | `project-log/AI_USAGE.md` as source | AI-usage declaration form |

Do not edit `SCORES.md`, `fdb_agent/` or run folders. If a number looks wrong, tell the lead instead of changing it.

## Where every number comes from
- `project-log/SCORES.md` is the source of truth (overall, per-slice, latency, failure counts).
- Raw evidence: `project-log/runs/2026-09-29_full_gemini3_8/` (baseline), `runs/2026-09-29_full_gate_gemini38_final/` (final pipeline; `score.txt` strict, `score_geminijudge.txt` judged), `runs/2026-09-29_decision_eval.json` (rules vs Jev decisions), `runs/2026-09-29_dev_*` (62-item practice set).
- Headline numbers: judged 61/100 (pipeline) vs 62/100 (baseline); strict 46 vs 50; first reply median 6.4 s vs 4.00 s.
- Paper numbers (arXiv 2604.04847) are verified in `RESEARCH_NOTE_FDB_AUTHORS.md`.
- If a number is not in SCORES.md, WORKLOG.md or a run folder, do not use it.

## Claims you must not make
- Do not claim we beat the baseline overall (61 vs 62 judged, 46 vs 50 strict). Say: gains in housing, self-correction, 3-tool; losses in e-commerce and pause.
- Do not claim any latency improvement or any latency figure that is not in SCORES.md (the pipeline's first reply is slower).
- The judge was **Gemini 2.5 Pro as a stand-in for GPT-4o**, not GPT-4o. Never call the numbers "GPT-4o-judged".
- Do not compare our numbers with the paper's as like-for-like.
- Do not say Smart Turn, escalation to a thinking model, or a local fallback is implemented. They are planned only.
- Retraction, backchannel and identifier-joining rules were added after the final run and are unit-tested only; do not attribute any benchmark result to them. `GATE_LEAN` is not in the submitted config.
- Do not attribute the housing gain to the gate alone (a prompt change was made at the same time, no ablation).
- Do not say we tuned on or looked at the 100 benchmark recordings. Tuning used our own 62-item practice set only.
- Do not claim the extension ran live unless someone has actually run it and recorded it (check WORKLOG). It uses mock tools.
- Do not claim `reproduce.sh` was verified on a clean machine (it was not, as of the last WORKLOG entry).
- Do not cite "human hesitation pauses of 600-900 ms": it is not in the paper.
- Do not say Smart Turn works on Indian-English accents (not checked).

## Submission checklist
- [ ] GitHub repo link works, README renders, no secrets or `.env` files committed
- [ ] Deck: max 8 slides, numbers match README
- [ ] Video: 3-5 minutes, unedited takes preferred, no untrue "live" claims (see the fallback lines in VIDEO_SCRIPT.md)
- [ ] AI-usage form filled from `AI_USAGE.md` (the form is not that file)
- [ ] Form submitted by **22:30 IST** (hard deadline 23:59 IST, 30 Sep 2026)
- [ ] Final `git push` done and the repo link in the form points to the pushed commit

## Known open items (be honest about them)
- No GPT-4o scoring, no second run for variance, no clean-machine run of `reproduce.sh`.
- Extension live run and video take depend on someone running `extension/ext_agent.py`.
