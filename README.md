# Commit Harness: an interruptible voice agent (Theme 05, Full-Duplex-Bench v3)

A voice agent that acts only on what the user finally meant, and recovers when a tool is slow or fails.
Gemini 3.8 Live does the talking; a small layer in front of the tools decides when an action may run.

## Result (100 real recordings)

| Agent | Judged pass | Strict pass | Typical reply delay |
|---|---|---|---|
| Stock agent (Gemini 3.8 Live, no harness) | 62 | 50 | 3.9 s |
| **Ours, submitted configuration** | **67** | **55** | 5.3 s |

- Judge: Gemini 2.5 Pro with the benchmark's own judge prompts, as a stand-in for GPT-4o. One run each.
- On 30 September we ran two configurations and submit the better one; both runs' logs are in the repo.
- No silent recordings in the submitted run. Run folder: `project-log/runs/2026-09-30_full_gate_gemini38_v2b/`.

## How it works

1. **Propose.** The voice model proposes a tool call.
2. **Settle.** The harness (`fdb_agent/gate.py`) holds it until the user's turn is over. Two deciders:
   word patterns ("um", "no, sorry") and a small classifier (TypeSafe Jev) that falls back to the patterns.
3. **Commit.** The call runs once. A correction replaces a held call, "never mind" withdraws it, a repeat is not re-run.

## What we found (and report)

- The harness changed what ran in only 2 of 100 recordings: the model proposes a call only after it thinks
  the user has finished. The gain over the stock agent comes from our prompt rules and an identifier
  formatting rule, which we did not test separately.
- We are one recording worse than the stock agent on self-corrections (7 of 17 against 8) and slower to reply.
- Ten failures were changes of mind after the action had already run. Only undo can fix those.

## Extension: in-car EV assistant

A recovery layer (`extension/recovery.py`) for slow and failing tools, run end to end on recorded audio:
a corrected reroute runs once, a failing charger lookup is retried quietly, a repeated booking is not made
twice, changing the time cancels the first booking before making the new one, and two failed roadside
requests end in a hand-off to a human. Mock tools, synthetic request voice, one run.
Evidence: `project-log/runs/2026-09-30_ext_car_e2e/` (conversation audio, recovery log).

## Reproduce

```bash
./reproduce.sh
```

Needs a LiveKit Cloud project and Gemini access, set by name in `.env.local` (no keys are in this repo).
Optional: a TypeSafe key (without it the patterns decide alone) and a judge key (without it scoring is
exact-match). About 2 hours for 100 recordings. Package versions are pinned in
`project-log/runs/env-freeze.txt`. Not yet run on a clean machine.

## Where things are

| Path | What |
|---|---|
| `fdb_agent/` | The benchmark agent, the harness and its tests |
| `extension/` | Recovery layer, in-car and home scenarios, their tests |
| `project-log/runs/` | Logs, decision logs, per-recording results and score reports for every run |
| `project-log/SCORES.md` | Every score and where it came from |
| `README_FULL.md` | Full write-up: design, all results, limitations, related work |
| `project-log/AI_USAGE.md` | AI assistants wrote most of the code and documents; the team made the decisions |
