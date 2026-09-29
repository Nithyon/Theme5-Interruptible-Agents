# Task board for the Sonnet session (assistant engineer)

The lead Claude session ("Theme 5 guidelines") assigns tasks here; the Sonnet session works them and fills in **Result**. Status: `todo` → `doing` → `done` (or `blocked` + a question). Rules: `project-log/README.md`, `GEMINI.md` (same hard rules apply: never read FDB-v3 test items or `ground_truth`, never handle API keys, no deleting or moving files unless the task says so, report honestly). Log notable work in `project-log/WORKLOG.md` too.

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
