# Task board for the Sonnet session (assistant engineer)

The lead Claude session ("Theme 5 guidelines") assigns tasks here; the Sonnet session works them and fills in **Result**. Status: `todo` → `doing` → `done` (or `blocked` + a question). Rules: `project-log/README.md`, `GEMINI.md` (same hard rules apply: never read FDB-v3 test items or `ground_truth`, never handle API keys, no deleting or moving files unless the task says so, report honestly). Log notable work in `project-log/WORKLOG.md` too.

---

## S9 — Extension: "slow / failing tool recovery" — design + offline core · status: done (2026-09-29)
**Result:** Chose the in-car assistant scenario (reroute/traffic/charging-station/booking/roadside-assistance). Wrote `extension/DESIGN.md` (scenario, 5 mock tools table, behaviors a-e each pointing at its test, mermaid diagram, "how this plugs into a LiveKit agent" section for the lead session to execute later, 60-90s demo script), `extension/recovery.py` (pure Python, no LiveKit imports: `ToolRunner` with timeout/retry-backoff, idempotency cache keyed by canonicalized args (reusing `gate.py`'s `_canon` pattern), `supersede(slot)` for cancel-on-interruption, `on_progress`/`on_handoff` callbacks, `EventLog`), `extension/mock_tools.py` (deterministic seed-controlled slow/flaky/state-changing tools), and `extension/test_recovery.py` (22 checks covering all 5 behaviors). One design decision worth flagging to whoever wires this in: a state-changing call that **times out** (as opposed to a plain `ToolFailure`) is never auto-retried at all, since the outcome is ambiguous — it goes straight to failure/handoff instead of risking a double-booking; this is tested explicitly. Ran the offline tests via `wsl -d Ubuntu -- bash -lc "~/theme5/fdb-env/bin/python .../test_recovery.py"` (had to use `bash -lc` — a bare `wsl -d Ubuntu -- ~/...` mis-resolves `~` to a Windows path and fails): **all 22 checks pass**. Did not touch `fdb_agent/gate.py`, `gate_agent.py`, or `baseline_agent.py`; did not start any agent or benchmark script; no API calls, no key values, no FDB-v3 data touched.
**Why:** 20% of the grade. The organizers asked to *showcase* exactly this (briefing notes fact 9: tasks fail, latency varies; retry, close the session, or hand off to a human; "you should be able to recover"), and to extend the "one mind talking, one mind thinking" idea. Camera is dropped (Round 1 has no video).
**Scope:** a **new use case outside the benchmark** (pick one: in-car assistant changing destination / booking a service, or a home-services booking line). Must be separate from the benchmark agent: **do not modify `fdb_agent/gate.py`, `gate_agent.py` or `baseline_agent.py`.**
**Do:**
1. `extension/DESIGN.md` (1 page): the scenario, 4–6 mock tools (at least one slow 3–8 s, one that fails intermittently, one state-changing), and the behaviours: (a) while a tool is slow, the talker keeps the user informed ("still checking…") without claiming it's done; (b) retry with backoff on failure, **never re-executing a state-changing call that already succeeded** (reuse the commit-gate idea: idempotency key per call); (c) user interrupts / changes their mind mid-wait → cancel or supersede the pending call; (d) after N failures → graceful handoff ("I've passed this to a human agent, reference #…"); (e) everything logged. Include a mermaid diagram and a 60–90 s demo script for the video.
2. `extension/recovery.py`: pure Python, **no LiveKit imports**: a `ToolRunner` with timeout, retry/backoff, idempotency keys, cancel/supersede, progress callbacks (for the talker to speak updates), handoff after N failures, and an event log. Plus `extension/mock_tools.py` with deterministic slow/failing behaviour controlled by a seed.
3. `extension/test_recovery.py`: offline tests for each behaviour (a)–(e). Run with the fdb env's python: `wsl -d Ubuntu -- ~/theme5/fdb-env/bin/python /mnt/d/Theme5-Interruptible-Agents/extension/test_recovery.py` (offline only; no network, no LiveKit).
4. A short "how this plugs into a LiveKit agent" section in DESIGN.md (the lead session wires it into a live agent after the gate run).
**Rules:** don't start any agent or benchmark script (the gate run is in progress). No API calls. No key values. Don't touch FDB-v3 data.
**Done when:** design + code + passing tests. Message the lead session.
**Result:**

---

## S8 — Draft the submission README and the slide outline · status: done (2026-09-29)
**Result:** Rewrote `README.md` (What it is · Architecture with mermaid diagram + 5 gate bullets · Why this design, citing only paper numbers verified in `RESEARCH_NOTE_FDB_AUTHORS.md`'s verification box (GPT-Realtime 0.600, self-correction 58.8%, cascaded 10.12s vs Gemini Live 3.1 4.25s) · Results table (baseline 50/100 exact-match from `SCORES.md` + gate row marked TBD + judge column marked TBD + paper rows) · Reproduce (env var names only, Gemini API key default / Vertex optional) · Extension placeholder (audio-only slow/failing tool recovery, explicitly marked not built) · Honest limitations · Declared models/APIs · AI usage · a short History note moving the old participant-kit description to the end). Deliberately did NOT cite the "600-900ms hesitation" figure since the verification box flags it as not actually in the paper. Wrote `project-log/SLIDES_OUTLINE.md`, 8 slides, each with bullets + a note on which figure/table it uses (mostly pointing back at the README's own diagram/tables rather than duplicating content). Didn't touch `fdb_agent/` code, no agents/benchmark scripts run, no key values written — env vars referenced by name only.
**Why:** 20% of the grade is docs/architecture/video ("an honest architecture explanation"; "what gap you identified and how you overcome it"). Deadline 30 Sep 11:59 PM IST.
**Do:**
1. Rewrite `D:\Theme5-Interruptible-Agents\README.md` as the submission README (keep anything still true from the current one; move participant-kit-era material to a short "History" note at the end). Sections: **What it is** (3 lines) · **Architecture** (one mermaid diagram: benchmark audio → LiveKit → Gemini 3.8 Live → commit gate → 12 tools; plus 5 bullets on the gate: hold until quiet 0.9 s, 1.8 s after hesitant words, supersede on correction, never run identical calls twice, only executed calls logged) · **Why this design** (cite the FDB-v3 paper's findings with the verified numbers in `project-log/RESEARCH_NOTE_FDB_AUTHORS.md`'s verification box and `INDUSTRY_BENCHMARKS.md`; no unverified numbers) · **Results** (table with baseline 50/100 strict from `project-log/SCORES.md`, a placeholder row for the gate run, a placeholder column for judge-scored numbers, and the paper's published rows) · **Reproduce** (link `reproduce.sh` and BUILD_PLAN §7; keys by *name* only; Gemini via API key by default, Vertex optional) · **Extension** (placeholder: audio-only "slow/failing tool recovery" use case, clearly marked) · **Honest limitations** (single run, exact-match until judge, cloud dependency, tuning only on our own devset, never on FDB-v3 items) · **Declared models/APIs** (Gemini 3.8 Live, LiveKit Cloud, GPT-4o judge, Parakeet via the benchmark) · **AI usage** (Claude, Gemini/Antigravity used as coding assistants; declaration form).
2. Write `project-log/SLIDES_OUTLINE.md`: at most 8 slides (problem, why agents fail, architecture, the gate, results, extension, limitations, next steps), with 3–5 bullets each and which figure/table goes on it.
**Rules:** only claims backed by our files or verified sources; mark every number that will change as `TBD`. Don't touch `fdb_agent/` code. No agents or benchmark scripts (the gate run is in progress). No key values.
**Done when:** README + outline written. Message the lead session.
**Result:**

---

## S7 — Organizer briefing: notes + what changes for us · status: done (2026-09-29)
**Result:** Wrote `project-log/meetings/2026-09-29_organizer_briefing_notes.md` — 18 key facts each with a verbatim quote, a "what changes for us" table (point → current state → action → owner) comparing against `STATUS.md`/`PLAN_VS_ACTUAL.md`, and 5 open questions to email. Flagged several likely transcription errors rather than treating them as fact: "16,000 A6000 GPU" (garbled, the reliable figure is the plainly-stated 48GB VRAM), "Gaoxuan" (almost certainly Guan-Ting Lin, the paper's actual verified first author), "prism@campaign.com" (conflicts with the PDF's assumed prism@samsung.com), a stray "40%" near the Bixby mention (contradicts the 20% stated everywhere else), and "30th of November" for the deadline (contradicts "take 30th as the deadline for now" said minutes earlier in the same meeting) — concluded 30 Sep 11:59 PM IST per STATUS.md, unchanged. Biggest actionable finding: the extension should reprioritize toward BUILD_PLAN_FDB_V3.md's "same coordinator, new adapter" approach with camera/video treated as optional (organizers confirmed FDB-v3 itself has no video in Round 1, and video-as-input is explicitly a Round 2 idea) — a camera-free extension scenario may be more time-efficient before the freeze. Also added "AI-usage declaration form" to STATUS.md's blocked-on-user checklist since it wasn't tracked there. No agents/benchmark scripts touched, no key values.
**Why:** the user shared the organizers' FDB-v3 briefing (auto-transcribed): `project-log/meetings/2026-09-29_organizer_briefing_transcript.md`. It's important: it clarifies scoring, reproduction, Gemini keys, deadline and what they value.
**Do:** write `project-log/meetings/2026-09-29_organizer_briefing_notes.md`:
1. **Key facts**, each with a short quote from the transcript. At least: scoring 60/20/20 and what counts; they re-run our code and **check run logs** ("people might quote some numbers, but the run logs will suggest something else"); "one-command" = a script wrapping all commands, not taken too literally; `--use-llm` judge optional / "report the numbers"; 48 GB limit only matters for our own checkpoints; **Gemini/Gemma preferred and "for Gemini and Gemma we will not need the key"** (what this means for Vertex vs API key); FDB-v3 has no video, so round 1 needs no vision; round 2 may add modalities; the extension should extend the "dual mind" idea (one mind talking, one thinking) and user experience / cost / latency savings earn points; recovery from tool failures and variable latency should be showcased (retry, close session, human in the loop); text output OK if voice is hard (state assumptions); Artificial Analysis as a reference; originality is checked; AI-usage **declaration form** must be filled; Bixby-related use case valued. **Deadline:** quote every statement (30 Sep, "move it to 4th October", "30th of November", "take 30th as the deadline for now") and conclude: plan for **30 Sep 11:59 PM IST**.
2. **What changes for us:** compare with `project-log/STATUS.md`, `PLAN_VS_ACTUAL.md` and the teammate plan in `STATUS.md` (Deadline section). A table: point → our current state → action (keep / change / add) → owner suggestion. Flag anything that contradicts what we're doing.
3. **Open questions to email the organizers** (short list).
Also note: this is probably the meeting that `PLAN_VS_ACTUAL.md` said was missing (`MEETING_2026-09-29_FDBv3_switch.md`).
**Rules:** transcript is auto-generated, so mark uncertain words (e.g. "16,000 A6000", the email address). No agents or benchmark scripts. No key values.
**Done when:** notes file written, readable in 5 minutes. Message the lead session.
**Result:**

---

## S6 — Survey current industry benchmarks for voice agents (tool use + interruptions) · status: done (2026-09-29)
**Result:** Wrote `project-log/INDUSTRY_BENCHMARKS.md`. Table covers FDB v1/v1.5/v2/v3, Artificial Analysis Speech-to-Speech Index, τ-bench/τ2-bench (has a new voice full-duplex mode), BFCL Audio, VoiceAgentBench, VoiceBench, FD-Bench — every row has a source URL and a verbatim quote I read on that page directly (via WebFetch), none copied from search-summary text without checking. One discrepancy flagged rather than resolved: a search summary said Qwen Audio 3.0 Realtime Plus leads the Artificial Analysis leaderboard at 84.1%, but my direct fetch of the live page showed Gemini 3.8 Live Extended Thinking (High) at 82.6 as #1 — noted both, didn't pick one to avoid inventing certainty (leaderboard changes live). Several other benchmarks found in search (Talking Turns, EVA-Bench, MTVA-Bench, M3-DuplexBench, etc.) were NOT included in the table because I didn't fetch a primary source for them — listed separately as "found but not verified," per the no-invented-numbers rule. Verdict on "which can we report on by 30 Sep": only FDB-v3 — the others either rank base models (Artificial Analysis, BFCL Audio, VoiceAgentBench — we can't enter our agent) or have no submission process (v1/v1.5/v2, VoiceBench, FD-Bench — citation-only). τ2-bench's new voice mode is architecturally closest to what we're doing but would need new tool bindings from scratch; not worth attempting before the freeze. No agents or benchmark scripts touched; no key values written.
**Why:** the user wants to know which public benchmarks measure what we build (a full-duplex voice agent that calls tools and survives interruptions/self-corrections), where FDB-v3 sits among them, and the best published numbers, for the README "results in context" section and a slide.
**Do:** web research, then write `project-log/INDUSTRY_BENCHMARKS.md`:
1. A table of benchmarks: name → what it measures (tool use / turn-taking / interruptions / disfluency / reasoning / latency) → voice or text → who runs it → official URL → latest top published results with **the system name and date**. Candidates to check (add others you find): Full-Duplex-Bench v1/v1.5/v2/v3; Artificial Analysis speech-to-speech (Big Bench Audio, conversational dynamics); tau-bench / tau2-bench and any voice variant; VoiceBench; other full-duplex or turn-taking benchmarks (e.g. FD-Bench, Talking Turns); any audio function-calling benchmark.
2. For FDB-v3 specifically: the paper's published per-system numbers (arXiv 2604.04847) and any newer results published since (GitHub issues, papers citing it, vendor blogs).
3. "Which ones could we realistically report on by 30 Sep": FDB-v3 is the scored one; say which others (if any) run with our LiveKit agent in < 2 h, and which only rank *models* (so we can't enter).
**Rules:** every number needs a source URL and a short verbatim quote (under 15 words) from that page, or "not found". **Never write a number you didn't read on the page.** Mark anything from secondary sources (news, blogs about someone else's results) as secondary. No agents or benchmark scripts (a run may be in progress). No key values.
**Done when:** the file exists and is readable in 5 minutes. Message the lead session.
**Result:**

---

## S5 — Write our own practice scenarios (dev set) for tuning the gate · status: done (2026-09-29)
**Result:** Wrote `devset/scenarios.jsonl` (40 scenarios, validated by parsing every line: unique ids, all 12 tools covered, 25/40 = 62.5% carry `self_correction`, 4 two-call turns, 4 three-call turns, 5 pure single-call controls + 7 more clean multi-call turns) and `devset/README.md` (field reference, coverage stats, and a local-Kokoro/Piper TTS proposal for turning this into audio — not installed or run). Built only from `AssistantFnc`'s 12 tool signatures in `lk_agent_tool.py` (read via `wsl -d Ubuntu`); never opened `benchmark_data_v2.json`, `fdb_v3_data_released/`, any `ground_truth`, `result_*.json`, or run logs. Noted in the README that this repo's actual tools don't chain by result id (e.g. no `flight_id` handoff) the way the PDF's `dual_agent.py` sketch assumed, so "level" here means call count per turn, not a value dependency chain. Didn't install or run anything, didn't start any agent.
**Why:** we may not tune on FDB-v3's 100 test recordings (participant guide §6: disqualification). We need our own spoken requests with disfluencies and self-corrections to tune the commit gate (quiet window, supersede rule) and later Jev.
**Source of truth for the tools:** only the tool definitions (names, parameters, descriptions) in `~/theme5/Full-Duplex-Bench/v3/lk_agent_tool.py` (class `AssistantFnc`). **Do not open** `benchmark_data_v2.json`, anything in `fdb_v3_data_released/`, any `ground_truth`, `result_*.json` or run logs under `project-log/runs/`. Write scenarios from scratch; don't imitate benchmark wording.
**Do:** create `D:\Theme5-Interruptible-Agents\devset\scenarios.jsonl` with **40 scenarios**, one JSON object per line: `id`, `domain`, `level` (1–3 chained calls), `disfluency` (list from: filler, pause, hesitation, false_start, self_correction), `utterance` (as spoken, with "um", "no wait", pauses marked `[pause 1.2s]`), `expected_calls` (ordered list of `{name, args}`), `must_not_call` (the stale call a naive agent would make), `expected_answer_gist` (one line). Mix: ≥50% self-corrections (argument change, tool change, cancel), some with two genuine calls in one turn (the gate must NOT merge them), some level-3 chains, 5 with no correction (control). Cover all 12 tools.
Then `devset/README.md`: the file's structure, and a short proposal for turning it into audio with a **local** TTS on the RTX 5070 (e.g. Kokoro or Piper, several voices, real pauses inserted), with install commands. **Don't install or run anything yet.**
**Rules:** no agents or benchmark scripts (a run may be in progress). No API calls. No key values.
**Done when:** 40 valid JSONL lines (check with a small Python parse) + README. Message the lead session.
**Result:**

---

## S1 — Find what is filling the C: drive (read-only) · status: done (2026-09-29)
**Why:** C: has 0 GB free, which broke WSL Ubuntu (its disk file is on C:). The user needs to know what to clean up.
**Do:** report the largest folders on C: (top 25, with sizes in GB), drilling into the big ones two levels deep: `C:\Users\saini` (Downloads, AppData\Local, AppData\Roaming, Documents, Desktop, OneDrive, .cache, `.conda`/`anaconda3`, pip/npm/uv caches), `C:\ProgramData`, `C:\Program Files*`, `C:\Windows\Temp`, `C:\$Recycle.Bin`, `C:\hiberfil.sys`, `C:\pagefile.sys`. Also list files over 5 GB anywhere on C:.
**Rules:** read-only. **Do not delete, move or compress anything.** Skip folders access is denied to and say so.
**Done when:** a table of the largest items plus a short list of "likely safe to clean" candidates (caches, temp, old installers, recycle bin), each marked with what it is. The user decides what to delete.
**Result:** (2026-09-29) Note first: `Get-PSDrive C` showed ~8.6 MB free when this ran — worse than `STATUS.md`'s "~47 GB free after the WSL move" note, so C: filled up again since that was written.

**Top-level C: (top 12 non-trivial, of 25 checked):**
| Path | Size |
|---|---|
| `Program Files (x86)` | 320.03 GB |
| `Program Files` | 53.06 GB |
| `Windows` | 36.11 GB |
| `ProgramData` | 20.13 GB |
| `$Recycle.Bin` | 0.38 GB |
| `OneDriveTemp` | 0.19 GB |
| `Python314` | 0.15 GB |
| everything else (XboxGames, Recovery, inetpub, java, maven, DRIVERS, etc.) | ≤0.04 GB each or 0 |

Note: `C:\Users` itself reported as 0 GB in a straight top-level scan — that's a scan artifact (access-denied on `CodexSandboxOffline` aborts naive enumeration), not the real size; see the drill-down below, which used per-subfolder scans and got real numbers.

**`C:\Users\saini` (top 15 of 25+ checked):**
| Path | Size | What it is |
|---|---|---|
| `AppData` | 161.06 GB | app caches/configs, see breakdown below |
| `Downloads` | 118.08 GB | mostly one folder, see breakdown below |
| `Videos` | 35.97 GB | user media — not ours to judge |
| `Documents` | 23.96 GB | user files |
| `SAM` | 11.15 GB | unknown project folder, not inspected further (out of scope) |
| `.cache` | 10.95 GB | **pip/uv/hf download cache — safe to clean** |
| `anaconda3` | 9.88 GB | conda install (only `Python314` and this repo's own `uv` env seem to actually be used; check before removing) |
| `WizTorrent` | 6.35 GB | torrent client data/downloads |
| `.ollama` | 5.33 GB | local LLM model weights — **safe to clean if not using local models**, but large re-download cost |
| `.vscode` | 5.03 GB | VS Code extensions/cache |
| `.codex` | 2.93 GB | Codex CLI data |
| `zodeck`, `.Neo4jDesktop2`, `My project`, `3dchatbot`, `zodeck-auth-pr`, `.gemini`, `bin`, `reviewanalyser`, `hivemind_scraper`, `netlfix-nitrostack`, `.antigravity-ide`, `realbot`, `bench`, `Projects` | 0.86–2.65 GB each | assorted personal/project folders, not inspected further |

**`AppData\Local` (top items):** `Google` 16.35 GB, `Programs` 14.97 GB, **`pip` 14.31 GB (cache — safe to clean, `pip cache purge`)**, **`npm-cache` 13.7 GB (safe to clean, `npm cache clean --force`)**, `Microsoft` 9.95 GB, `Docker` 7.67 GB (image/volume data — only if Docker unused), `Packages` 6.35 GB (Store app data), `hermes` 5.27 GB, `Roblox` 3.78 GB, `Perplexity` 2.17 GB, `ms-playwright` 2.02 GB (browser binaries — safe to clean, reinstallable), `Ollama` 1.47 GB, **`Temp` 1.17 GB (safe to clean)**.

**`AppData\Roaming` (top items):** `Claude` 10.26 GB (this app's own data/history — do not touch while sessions are running), `com.yaps` 7.19 GB, `Python` 6.36 GB, `Code` 4.66 GB (VS Code), `Notion` 3.23 GB, `npm` 3.17 GB, `stremio` 1.68 GB, `anytype` 1.29 GB, `Cursor` 1.03 GB.

**`AppData\LocalLow`:** trivial, <0.1 GB total.

**`Downloads` breakdown:** the 118 GB is almost entirely **one folder, `geospatial` (84.13 GB)** — not inspected further (out of scope / likely large raster/vector datasets). Everything else is small: `Screen Recordings` 1.7 GB, `reuters_8.5M_titles` 1.33 GB, `bloomberg_news` archive 1.28 GB, several `.zip` exports from Google Takeout/Drive (each under 4 GB, listed below), a couple of movie files (`.mkv`/`.mp4`, ~0.7 GB each), and installer `.exe` files (Docker Desktop 0.61 GB, Neo4j Desktop 0.54 GB). Loose files >0.5 GB directly in Downloads: `exact_diagram.drawio.zip` 4.09 GB, `takeout-...zip` 3.67 GB, `CG_Live_Demo_2.zip` 1.71 GB, several `runs-`/`geo_env-`/`raw_data-` Drive-export zips (0.6–1.04 GB each), `ml datasets ....zip` 0.71 GB.

**`ProgramData` (top items):** `NVIDIA Corporation` 7.42 GB, `Anytxt` 3.24 GB (a file-search-index app — its index cache is usually safe to clean), `Corsair` 2.19 GB, `Lenovo` 1.55 GB, `Epic` 1.48 GB, `NVIDIA` 1.08 GB, `Package Cache` 0.72 GB (**MSI installer cache — often safe to clean, but can break future uninstalls of older MSI apps**), `Microsoft` 0.6 GB, `saini` 0.59 GB, `MySQL` 0.56 GB.

**`Program Files` (top items):** `Unity` 12.59 GB, `Lenovo` 10.17 GB, `Microsoft Office` 4.61 GB, `Docker` 3.98 GB, `QGIS 3.44.8` 2.9 GB, `MongoDB` 2.54 GB, `MySQL` 2.29 GB, `Neo4j Desktop 2` 1.14 GB, `NVIDIA Corporation` 1.07 GB, `BraveSoftware` 1.04 GB.

**`Program Files (x86)` — the single biggest item on the whole drive is here:** `Steam` = **311.17 GB**, almost the entire 320 GB folder. Installed games (top 4, `steamapps\common`): **Grand Theft Auto V 119.05 GB**, **Grand Theft Auto V Enhanced 95.27 GB** (both GTA V editions installed at once), **FC 26 57.63 GB**, **Phasmophobia 37.73 GB**. This is by far the largest, single clearest cleanup target if any of these aren't being actively played — reinstallable from Steam any time.

**`Windows\Temp`:** only 0.03 GB — not a factor.

**`$Recycle.Bin`:** 0.38 GB — small, but 100% safe to empty.

**`hiberfil.sys` / `pagefile.sys` / `swapfile.sys`:** none exist at `C:\` (checked individually with `Get-Item -Force`) — hibernation/pagefile aren't stored there, so not a factor.

**Files >5 GB anywhere on C::** none found in the parts of the drive that could be scanned. (Scan skipped, access-denied: `Program Files\WindowsApps`, `Windows\appcompat\AIDD` and other protected system subpaths, `ProgramData\Lenovo\SmartEngine\logs`, `Users\CodexSandboxOffline`, `$Recycle.Bin\S-1-5-18`, `System Volume Information`, `PerfLogs` — all standard OS/other-user protected paths, consistent with running as a normal user account.)

### Likely safe to clean, ranked by size
1. **Steam games not currently being played** (`Program Files (x86)\Steam\steamapps\common`) — up to ~310 GB: GTA V (119 GB) + GTA V Enhanced (95 GB) + FC 26 (58 GB) + Phasmophobia (38 GB). By far the biggest win; all reinstallable.
2. **`Downloads\geospatial`** (84 GB) — unknown dataset, only the user can judge if it's still needed.
3. **`.cache`** (11 GB) + **`AppData\Local\pip`** (14.3 GB) + **`AppData\Local\npm-cache`** (13.7 GB) — pure package caches, safe to purge (`pip cache purge`, `npm cache clean --force`, delete `.cache`), all just get rebuilt on next install.
4. **`.ollama`** (5.3 GB) — local model weights, safe to delete if not using local LLMs (re-downloads on next `ollama pull`).
5. **`ms-playwright`** (2 GB) — browser binaries, reinstallable (`npx playwright install`).
6. **`ProgramData\Package Cache`** (0.72 GB) — MSI installer cache; safe in most cases but can occasionally be needed by an app's own uninstaller.
7. **`$Recycle.Bin`** (0.38 GB) — trivial but 100% safe, just empty it.
8. **Loose Google Takeout/Drive export `.zip` files in `Downloads`** (`takeout-...zip` 3.67 GB, several `runs-`/`geo_env-`/`raw_data-` exports totaling ~5 GB) — worth checking if already extracted/used elsewhere before deleting.
9. **`WizTorrent`** (6.35 GB) — torrent client's own downloaded/seeding data; only safe if nothing there still needs seeding.

Not evaluated (out of scope / needs the user's judgment, not size-driven): `Videos` (36 GB), `Documents` (24 GB), `SAM` (11 GB), `anaconda3` (9.9 GB, may still be in use), `.vscode`/`.codex`/`.gemini`/project folders under `saini\` — these are working data, not caches.

---

## ⚠ While a benchmark run is in progress (check: `wsl -d Ubuntu -- bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/progress.sh gemini3_8`, "processes" > 0)
**Do not start any agent, `lk_agent_tool.py`, `baseline_agent.py`, `gate_agent.py`, `run_*` or `smoke_one.sh`.** A second agent worker on the same LiveKit project steals recordings from the running benchmark and ruins its score. Reading files and writing docs is fine.

---

## S3 — Compare the build-plan PDF with what has actually been built · status: done (2026-09-29)
**Result:** Wrote `project-log/PLAN_VS_ACTUAL.md`. Key finding: the PDF's `dual_agent.py` (cascaded STT→talker/reasoner→TTS) was never built — what exists is `BUILD_PLAN_FDB_V3.md`'s Option A (`gate_agent.py`: speech-to-speech `gemini-3.8-live` + a gate wrapping the stock tools). Flagged an unresolved conflict: PDF's "tune on a 20-example dev set" vs. `DECISIONS.md`'s "never tune on FDB-v3 test items" — these read as contradictory unless "dev set" means the team's own synthetic recordings (BUILD_PLAN's actual proposal). Also flagged: gate has no end-to-end scored run yet (offline tests only, 7/7); NON_BLOCKING model behavior while a call is held is unchecked; two secrets (LiveKit, AWS key) pasted in chat with rotation unconfirmed; `VERIFICATION.md`/`MEETING_2026-09-29_FDBv3_switch.md` referenced by the PDF as "Done" but not found anywhere in the repo tree (marked unverified, not assumed missing-but-fine). Did not open any FDB-v3 test items.
**Why:** the user wants to know how the current work lines up with their plan document.
**Inputs:** the plan `D:\Downloads\Theme 05 Build Plan — FDB-v3.pdf` (read it with a PDF tool); our repo plan `D:\Theme5-Interruptible-Agents\BUILD_PLAN_FDB_V3.md`; what exists: `project-log/STATUS.md`, `WORKLOG.md`, `DECISIONS.md`, `SCORES.md`, code in `D:\Theme5-Interruptible-Agents\fdb_agent\` (`gate.py`, `gate_agent.py`, `baseline_agent.py`, `models.py`, `test_gate.py`).
**Do:** write `project-log/PLAN_VS_ACTUAL.md` with a table: each item in the PDF → status (done / in progress / not started / changed) → evidence (file or log line) → note. Then a short section "Differences that matter" covering where the PDF and reality disagree, e.g. model choice (now Gemini 3.8 Live via **Vertex AI**, because the org policy blocks API keys and AI Studio prepay was empty), judge (no OpenAI key yet → exact-match scoring), GPU (laptop RTX 5070 + AWS g5 in Hong Kong for the clean-machine test), Jev (not started; plugs into the gate's "is the user done?" decision), extension/video (not started). Finish with "Open risks" (e.g. organizers re-running a Vertex agent need their own Google Cloud login).
**Rules:** read-only except the new file. Never open FDB-v3 test items or `ground_truth`. Don't guess: if the PDF says something you can't verify, mark it "unverified".
**Done when:** the file exists and the user can read it in 3 minutes. Message the lead session.
**Result:**

---

## S4 — Draft the one-command reproduction script (don't run it yet) · status: done (2026-09-29)
**Result:** Drafted `reproduce.sh` (repo root) and a "Reproducing our score" section in `BUILD_PLAN_FDB_V3.md` (§7). Script: apt/dnf detection → install uv → clone Full-Duplex-Bench (pinned commit — see assumption below) → build env from `project-log/runs/env-freeze.txt` → download+extract data like G1 did → check env vars by name only (never reads/prints values) → run agent + `run_tool_benchmark_all_released.py` + `score_summary.sh`, modeled on `project-log/scripts/run_baseline.sh`. Did not run it (a 100-recording run is in progress). Biggest gap found: no Full-Duplex-Bench commit hash is recorded anywhere in the repo, so `FDB_COMMIT` is currently empty — flagged as the top assumption to fix before this is trustworthy. Other unverified assumptions listed in BUILD_PLAN_FDB_V3.md §7 (v3/requirements.txt existence, AL2023 ffmpeg availability, gdown non-interactive reliability). Never opened FDB-v3 test items, never wrote a key value, didn't touch WSL or start any agent.
**Why:** the submission must re-run on a clean Linux GPU machine (organizers: one 48 GB NVIDIA GPU). Later we test it on the AWS box (Amazon Linux 2023, `dnf`) and it must also work on Ubuntu (`apt`).
**Do:** draft `D:\Theme5-Interruptible-Agents\reproduce.sh` plus a README section "Reproducing our score" that: installs system deps (ffmpeg, git, curl; detect `apt` vs `dnf`), installs `uv`, clones Full-Duplex-Bench at the commit in `project-log/runs/env-freeze.txt`, builds the Python env from that freeze file, downloads the FDB-v3 data the same way G1 did (see `GEMINI_TASKS.md`), checks required env vars by **name only** (LIVEKIT_URL/API_KEY/API_SECRET, and either GOOGLE_API_KEY or GOOGLE_GENAI_USE_VERTEXAI+GOOGLE_CLOUD_PROJECT with ADC), then runs our agent + the 100-recording benchmark + scoring (model it on `project-log/scripts/run_baseline.sh`, with the agent script as a parameter).
**Rules:** don't execute the script, and don't start any agent (see the warning above). Never write key values anywhere. Use `set -euo pipefail` and clear error messages.
**Done when:** script + README section drafted and a list of assumptions you couldn't check. Message the lead session.
**Result:**

---

## S2 — Guide the user through LiveKit keys and verify the connection · status: done (2026-09-29, verified by the lead session: `LiveKit: connected OK`; Gemini key also OK)
**Why:** the benchmark needs a LiveKit Cloud project. The user created project "samsung" (id p_5was69xkkfr, region US) and now needs its keys saved in WSL.
**Do:**
1. Guide the user (in plain steps) through LiveKit dashboard → Manage API keys → Create key, and saving these lines **themselves** in WSL file `~/theme5/Full-Duplex-Bench/v3/.env.local` (e.g. `nano`): `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `GOOGLE_API_KEY` (their Gemini key). The API secret is shown only once.
2. **Never ask for, read, print or paste the values.** Don't `cat` the file. The user types them.
3. Verify with the ready-made script (prints names only, then a free test connection):
   `wsl -d Ubuntu -- ~/theme5/fdb-env/bin/python /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/check_livekit.py`
4. If the connection fails, help the user fix the value (wrong URL format, stray quotes/spaces), without seeing it.
**Done when:** the script prints `LiveKit: connected OK`. Record the script output here (it contains no secrets) and tell the lead session.
**Result:**
