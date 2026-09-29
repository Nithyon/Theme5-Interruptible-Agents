# Status

_Last updated: 2026-09-29. Update this file whenever the state or the next step changes._

## Where we are
- **Target changed.** The updated guide (`Theme05_Participant_Guide_UPDATED_FBD.docx`, 2026-09-26) scores Round 1 as: 60% Full-Duplex-Bench v3 re-run, 20% use-case extension, 20% docs/architecture/video. The participant-kit harness no longer decides the score.
- **Plan written:** [`BUILD_PLAN_FDB_V3.md`](../BUILD_PLAN_FDB_V3.md). Core idea: a LiveKit agent with a commit gate so tools run only after the user's turn is final.
- **Existing work (participant-kit agent):** complete and tested, weighted 83.7 on the kit's evaluator. Parts reusable for FDB-v3: cancellation/supersession, idempotency, argument validation, claim lint, self-correction handling. Candidate for the extension (camera troubleshooting).
- **Codex:** paused by the user on 2026-09-29. Claude does the work; no handoff updates for now.

## Resolved 2026-09-29
- C: filled up (0 GB) and broke WSL. Ubuntu's disk is now at `D:\WSL\Ubuntu\ext4.vhdx`; C: has ~47 GB free. Everything inside Ubuntu survived. C: is still nearly full overall; Sonnet's S1 survey will say what's safe to clean.
- Parakeet ASR (scoring) runs on the RTX 5070: 4.7 GB GPU memory.

## Deadline
- **30 Sep 2026, 11:59 PM IST; Google Form by 22:30 IST** (from the teammate's upgrade plan, `D:\Downloads\ur-gonna-code-from-synthetic-kurzweil.md`). Jev cut. A full 100-recording run takes ~1 h 45 min and runs can't overlap on one LiveKit project, so plan at most 2 full runs on 30 Sep (gate check AM, frozen final PM).
- Teammate plan reviewed 2026-09-29: keep dual auth (API key or Vertex), Azure gpt-4o judge (check real quota first), dev-set audio + pause scenarios, fresh-clone test. Hold rule and supersede/dedupe already in `gate.py`. Collaborate via the private repo (branches/PRs), not zips.

## Code repository
- **Private GitHub repo:** https://github.com/Nithyon/Theme5-Interruptible-Agents (created 2026-09-29, branch `main`). Commits use the account's noreply email. `.gitattributes` keeps `.sh`/`.py` as LF. Excluded: `.venv/`, `docs-source/` (organizer guide), `.env*`; keys live only in WSL `~/theme5/Full-Duplex-Bench/v3/.env.local`, never in the repo.
- Push the full baseline run folder (`project-log/runs/2026-09-29_full_gemini3_8/`) after the run finishes; it also holds a stale report from the aborted first run, so replace that first.
- Before submission: organizers need access (add them as collaborators, or make it public), and check that run reports containing benchmark expected answers are OK to share.

## AWS GPU box
- **Stopped** (2026-09-29, by the user). A10G 24 GB, Amazon Linux 2023, `ssh -i ~/.ssh/nithiyon-gpu.pem ec2-user@ec2-16-106-29-14.ap-east-1.compute.amazonaws.com` (from WSL). **Stop it when idle (~$1.87/h).** Rotate the key pair (it was exposed in chat) **on the day we next start it**: user makes a new key locally (never in chat), Claude logs in once with the old key, adds the new public key to `~/.ssh/authorized_keys`, removes the old; then user deletes `hahaha.pem` and the old EC2 key pair. The instance itself is kept.

## Blocked on the user
- [ ] Free LiveKit Cloud account → `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` in `v3/.env.local` (typed by the user, not pasted in chat)
- [ ] OpenAI API key (needed for the gpt-4o judge regardless of agent model)
- [ ] TypeSafe API key (`TYPESAFE_API_KEY`) for the Jev decision layer, when we get to the commit gate
- [x] WSL2 Ubuntu installed (already there; Python 3.12.3, GPU visible: RTX 5070, driver 592.07, 922 GB free)
- [x] DNS inside WSL fixed (2026-09-29)
- [x] ffmpeg installed in WSL
- [x] Python env `~/theme5/fdb-env`: Python 3.10.21, torch 2.11.0+cu128 (GPU works), livekit-agents 1.8.3, NeMo 3.0.0. Versions in `runs/env-freeze.txt`. Note: `~=1.3` resolved to livekit-agents 1.8.3; check the templates still run on it, else pin 1.3.x.
- [x] Antigravity CLI `agy` 1.2.13 installed (junior assistant; Gemini CLI's Google sign-in is discontinued)
- [x] Benchmark audio: 100 recordings in `~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released/` (905 MB)
- [x] LiveKit + Gemini keys in `.env.local`; end-to-end smoke test passed (2026-09-29)
- [ ] Judge key: OpenAI key, or Nebius (read-only mode when tried) — until then scoring is exact-match
- [ ] **Use Vertex AI via ADC** (the org policy on `hackathon-cinemahackathon` disallows API keys): user runs Google's `setup_adc.sh` in WSL with that project; then `scripts/check_vertex.py` lists Live models; agents support Vertex via `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`. Open question for submission: organizers would need their own Google Cloud login to re-run a Vertex agent.
- [ ] (superseded) **Gemini key needs billing:** its AI Studio project is on prepaid credit, now empty (`prepayment credits are depleted`). Fix: a Gemini key billed to the Cloud billing account with the trial credits (project `hackathon-cinemahackathon`), or top up the prepay.
- [ ] Full 100-recording baseline (user approved 2026-09-29; blocked on the billing fix)
- [x] Commit gate code + offline tests (7/7)
- [ ] Gate run: check for **false "done" claims** (participant guide §1: "no false 'done!' claims"). Gemini 3.8 tools are NON_BLOCKING by default, so the model may confirm an action while the gate still holds it. If seen, make held tools blocking or have the model wait for the result before confirming.
- [ ] Judge key before final numbers (guide §5: organizers run with the LLM judge on).
- [ ] Submission route: organizers re-run on "declared hosted APIs" with their own credentials (guide §5), so decide Vertex vs an API-key provider; declare Jev/TypeSafe if used.
- [ ] Submission deadline
- [ ] Team name for `submission.yaml` (kit only)

## Next steps (in order)
1. Set up FDB-v3 in WSL2 (Python 3.10 conda env, ffmpeg, NeMo ASR, benchmark audio).
2. Baseline run with one stock template; save logs to `project-log/runs/`.
3. Commit gate on the realtime template; re-run; compare disfluency and rollback breakdowns.
4. Own practice set of disfluent recordings (never tune on the test items).
5. Extension: camera device troubleshooting as a LiveKit agent.
6. Submission package: one-command script, README + diagram, run logs, 3–5 min video, ≤ 8 slides.

## Open questions
- ~~Do LiveKit's plugins accept the newer model ids?~~ Yes (G2): `gemini-3.8-live` and `grok-voice-think-fast-2.0` are in the installed plugins; OpenAI plugin defaults to `gpt-live-1`.
- Confirm with organizers that the participant-kit harness is retired (the guide is newer and explicit).
- `book_flight` in the templates takes only `passenger_name`; check how the judge treats an expected `flight_id` reference.
