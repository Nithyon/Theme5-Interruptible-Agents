# Decisions

Each entry: date, decision, why, who decided. Add new ones at the top.

| Date | Decision | Why | By |
|---|---|---|---|
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
