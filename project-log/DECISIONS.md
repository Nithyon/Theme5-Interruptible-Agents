# Decisions

Each entry: date, decision, why, who decided. Add new ones at the top.

| Date | Decision | Why | By |
|---|---|---|---|
| 2026-09-29 | Jev integrated and verified live: `fdb_agent/jev.py` (`JevJudge`, `typesafe_sdk.AsyncTypeSafeClient.system_one`, typed `Choice` questions read from `.choices[name].probabilities`), wired into `gate.py`'s `required_quiet()` and the supersede loop, with a **rules-only fallback on `None`/timeout** so a slow or failing Jev call never blocks or fails a turn. 18/18 offline tests pass (commit `7ea065c`). Live ping with the real key: `turn_state` "complete" 0.99 in 466ms, "continuing" 1.0 in 350ms, "correction" 1.0 in 358ms — well under the gate's 0.9s base quiet window. SDK `typesafe-sdk` 0.7.2 installed in `fdb-env`. Dev-set A/B (rules-only vs. gate+Jev, via S11's `run_dev.sh`/`score_dev.py`) in progress — kept only if it beats the rules-only gate per the original decision below. | Confirms the fallback design was the right call: Jev adds real value (sub-500ms typed judgments) without becoming a new point of failure, since every call site degrades cleanly to the existing heuristic. | Lead session (implementation + verification) |
| 2026-09-29 | Add TypeSafe Jev as a decision layer on top of the voice model (commit gate: turn final?, correction type?, duplicate?) | Fast typed decisions can commit earlier than a silence timeout (latency) and classify corrections; keep only if it beats the rules-only gate on our dev set | User (direction), Claude (design) |
| 2026-09-29 | Pause Codex; Claude works alone for now | User's call | User |
| 2026-09-29 | FDB-v3 agent: commit gate first on a realtime template, cascaded pipeline only if needed | Strict pass rate fails any early/extra call; wrapping 12 tools is the fastest fix for the biggest failure mode | Claude (proposed), awaiting user go-ahead |
| 2026-09-29 | Never tune on FDB-v3 test items; build our own practice recordings | Guide: disqualifying | Guide rule |
| 2026-09-29 | Log every tool execution honestly; defer execution instead of hiding calls | Deferring is the asked-for behavior; hiding executed calls would be gaming | Claude |
| 2026-09-27 | Drive backup excludes `.venv` and `__pycache__` | Machine-specific, rebuildable | Claude |
| 2026-09-26 | Treat the updated guide (FDB-v3) as the current scoring; confirm with organizers | Newer and explicit | Claude (recommendation) |
| 2026-09-26 | No contact with the "Amazon ML Challenge setup" session | User's instruction | User |
| 2026-09-24 | Additive corrections cancel and re-issue the search | Old and new calls can't be told apart by the scorer's subset rule; re-issuing matches the requested call | Claude |
| 2026-09-24 | Claude implements `agent/`; Codex reviews | User's choice | User |
| 2026-09-24 | No speculative tool calls before end of turn | Stale-call penalties and shifted mock delays | Claude + Codex |
| 2026-09-21 | No attribution trailer on commits | User's preference | User |
