#!/usr/bin/env bash
# Reproduce our FDB-v3 score from a clean Linux GPU machine (one 48 GB NVIDIA GPU,
# or any CUDA GPU for a smaller smoke test) — the organizers' GPU is used only by the
# benchmark harness's own Parakeet ASR; our agent and Gemini 3.8 Live never touch it.
#
# What this does, in order:
#   1. install system deps (ffmpeg, git, curl) via apt or dnf
#   2. install uv
#   3. clone Full-Duplex-Bench at the pinned commit
#   4. build the Python env from project-log/runs/env-freeze.txt
#   5. download and extract the FDB-v3 data (same steps G1 used)
#   6. check required env vars by NAME ONLY (never print or log a value)
#   7. run the final commit-gate agent + the 100-recording benchmark + scoring
#
# Usage:
#   ./reproduce.sh [agent_script] [provider]
#   Defaults to our submitted config: fdb_agent/gate_agent.py, provider gate_gemini38_final,
#   with GATE_COMBINE=either (rules + Jev as one decider) and the rest of the final gate
#   settings exported below — this matches project-log/scripts/full_run_final.sh exactly.
#   For the stock baseline instead: ./reproduce.sh fdb_agent/baseline_agent.py gemini3_8
#
# Requires beforehand (typed by you, never by this script), in FDB_V3_DIR/.env.local:
#   Required: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, GOOGLE_API_KEY (a plain
#     Gemini API key — the default path; set GOOGLE_GENAI_USE_VERTEXAI=true instead only if
#     you need Vertex AI + ADC, e.g. `gcloud auth application-default login` already run).
#   Optional: TYPESAFE_API_KEY (Jev typed-classifier layer on the gate — if absent, the gate
#     falls back to rules-only automatically; this script just tells you which mode you're in).
#   Optional: OPENAI_API_KEY (or OPENAI_BASE_URL for an Azure deployment) — enables the
#     organizers' GPT-4o judge scoring; without it, scoring falls back to exact-match.
#
# Does NOT run itself as part of any CI/automatic step. Do not run this while another
# agent or benchmark process is using the same LiveKit project or /tmp/agent_tool_calls.log.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FDB_REPO_URL="https://github.com/DanielLin94144/Full-Duplex-Bench"
FDB_COMMIT="${FDB_COMMIT:-3e799c45a045256f47d5f1c9cda90157e2d2ec9e}"  # FDB checkout used for our runs (2026-09-29)
FDB_DIR="${FDB_DIR:-$HOME/theme5/Full-Duplex-Bench}"
FDB_V3_DIR="$FDB_DIR/v3"
ENV_DIR="${ENV_DIR:-$HOME/theme5/fdb-env}"
ENV_FREEZE="$REPO_ROOT/project-log/runs/env-freeze.txt"
DATA_GDRIVE_ID="1SO_4MTazWQ_jvCx0dtmpQ-t40bdd07yz"   # from v3/README.md, per GEMINI_TASKS.md G1

AGENT_SCRIPT="${1:-$REPO_ROOT/fdb_agent/gate_agent.py}"
PROVIDER="${2:-gate_gemini38_final}"

# Final gate settings — matches project-log/scripts/full_run_final.sh exactly. Only takes
# effect for gate_agent.py; harmless (unused) when running baseline_agent.py instead.
export GATE_COMBINE="${GATE_COMBINE:-either}"
export GATE_JEV="${GATE_JEV:-1}"
export GATE_DRAFT_HOLD_S="${GATE_DRAFT_HOLD_S:-2.5}"
export GATE_DANGLING="${GATE_DANGLING:-1}"
export GATE_PROMPT="${GATE_PROMPT:-2}"
export GATE_QUIET_S="${GATE_QUIET_S:-0.9}"
export GATE_HESITANT_QUIET_S="${GATE_HESITANT_QUIET_S:-1.8}"
# Switches added after the reported run (2026-09-29_full_gate_gemini38_final). Pinned off so
# this script reproduces the reported configuration exactly; set to 1 to try the newer gate.
export GATE_RETRACT="${GATE_RETRACT:-0}"
export GATE_ID_NORMALIZE="${GATE_ID_NORMALIZE:-0}"
export GATE_BACKCHANNEL="${GATE_BACKCHANNEL:-0}"
export GATE_LEAN="${GATE_LEAN:-0}"
export GATE_SMART_TURN="${GATE_SMART_TURN:-0}"

log() { echo "[reproduce] $*"; }
die() { echo "[reproduce] ERROR: $*" >&2; exit 1; }

# --- 1. system deps: detect apt vs dnf -----------------------------------------------
install_system_deps() {
  if command -v apt-get >/dev/null 2>&1; then
    log "installing system deps via apt (Ubuntu)"
    sudo apt-get update -y
    sudo apt-get install -y ffmpeg git curl
  elif command -v dnf >/dev/null 2>&1; then
    log "installing system deps via dnf (Amazon Linux 2023 / Fedora)"
    sudo dnf install -y ffmpeg git curl || {
      log "ffmpeg not in default AL2023 repos; trying the RPM Fusion / EPEL path"
      die "install ffmpeg manually on this distro, then re-run"
    }
  else
    die "neither apt-get nor dnf found; install ffmpeg, git, curl manually"
  fi
}

# --- 2. uv ----------------------------------------------------------------------------
install_uv() {
  if command -v uv >/dev/null 2>&1; then
    log "uv already installed: $(uv --version)"
    return
  fi
  log "installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  command -v uv >/dev/null 2>&1 || die "uv install did not put uv on PATH"
}

# --- 3. clone Full-Duplex-Bench at the pinned commit -----------------------------------
clone_fdb() {
  if [ -d "$FDB_DIR/.git" ]; then
    log "Full-Duplex-Bench already cloned at $FDB_DIR"
  else
    log "cloning Full-Duplex-Bench into $FDB_DIR"
    git clone "$FDB_REPO_URL" "$FDB_DIR"
  fi
  if [ -n "$FDB_COMMIT" ]; then
    git -C "$FDB_DIR" checkout "$FDB_COMMIT"
  else
    log "WARNING: no pinned commit set (FDB_COMMIT empty); using whatever HEAD the clone gives you"
  fi
  [ -d "$FDB_V3_DIR" ] || die "expected $FDB_V3_DIR after clone; repo layout may have changed"
}

# --- 4. Python env from the freeze file ------------------------------------------------
build_env() {
  [ -f "$ENV_FREEZE" ] || die "missing $ENV_FREEZE; run project-log/scripts/setup_fdb_env.sh once and freeze it first"
  if [ -d "$ENV_DIR" ]; then
    log "env dir $ENV_DIR already exists, reusing it"
  else
    log "creating Python 3.10 env at $ENV_DIR"
    uv venv --python 3.10 "$ENV_DIR"
  fi
  # shellcheck disable=SC1091
  source "$ENV_DIR/bin/activate"
  uv pip install -r "$ENV_FREEZE"
  uv pip install -r "$FDB_V3_DIR/requirements.txt" 2>/dev/null || \
    log "no v3/requirements.txt found or already covered by env-freeze.txt"
}

# --- 5. download + extract the FDB-v3 data ---------------------------------------------
fetch_data() {
  if [ -d "$FDB_V3_DIR/fdb_v3_data_released" ] && \
     [ "$(find "$FDB_V3_DIR/fdb_v3_data_released" -name input.wav | wc -l)" -eq 100 ]; then
    log "data already present (100 input.wav found)"
    return
  fi
  log "downloading FDB-v3 data (gdrive id $DATA_GDRIVE_ID)"
  uv pip install gdown
  mkdir -p "$HOME/theme5/downloads"
  gdown "$DATA_GDRIVE_ID" -O "$HOME/theme5/downloads/fdb_v3_data_released.zip"
  python3 - "$FDB_V3_DIR" "$HOME/theme5/downloads/fdb_v3_data_released.zip" <<'PY'
import sys, zipfile
dest, zip_path = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(zip_path)
members = [m for m in z.namelist() if not m.startswith("__MACOSX")]
z.extractall(dest, members=members)
print("extracted", len(members), "entries into", dest)
PY
  n=$(find "$FDB_V3_DIR/fdb_v3_data_released" -name input.wav | wc -l)
  [ "$n" -eq 100 ] || die "expected 100 input.wav files, found $n"
}

# --- 6. check required env vars by NAME ONLY -------------------------------------------
check_env_vars() {
  local envfile="$FDB_V3_DIR/.env.local"
  [ -f "$envfile" ] || die "missing $envfile — create it yourself with the required keys (see README: Reproducing our score)"

  local missing=()
  for v in LIVEKIT_URL LIVEKIT_API_KEY LIVEKIT_API_SECRET; do
    grep -q "^${v}=.\+" "$envfile" || missing+=("$v")
  done

  # Default auth path is a plain GOOGLE_API_KEY (Gemini API) — this is what the organizers'
  # note "for Gemini we will not need the key" describes as the expected reproduction path.
  # Vertex AI + ADC is only used if GOOGLE_GENAI_USE_VERTEXAI=true is explicitly set (that's
  # our own dev-environment path, required because our org's Cloud policy blocks plain keys).
  local have_google_key=0 have_vertex=0
  grep -q '^GOOGLE_API_KEY=.\+' "$envfile" && have_google_key=1
  if grep -q '^GOOGLE_GENAI_USE_VERTEXAI=true' "$envfile" && \
     grep -q '^GOOGLE_CLOUD_PROJECT=.\+' "$envfile"; then
    have_vertex=1
    gcloud auth application-default print-access-token >/dev/null 2>&1 || \
      log "WARNING: GOOGLE_GENAI_USE_VERTEXAI is set but 'gcloud auth application-default login' does not look done"
  fi
  if [ "$have_google_key" -eq 0 ] && [ "$have_vertex" -eq 0 ]; then
    missing+=("GOOGLE_API_KEY (or GOOGLE_GENAI_USE_VERTEXAI+GOOGLE_CLOUD_PROJECT with ADC)")
  fi

  if [ "${#missing[@]}" -gt 0 ]; then
    die "missing required variables in $envfile (names only, never their values): ${missing[*]}"
  fi
  log "required env vars present in $envfile (names checked only, no values read or printed)"

  # TYPESAFE_API_KEY is optional: the gate's Jev integration (fdb_agent/jev.py) already
  # falls back to rules-only on any failure, including a missing key — this is just telling
  # you which mode you're about to run in, not a hard requirement.
  if grep -q '^TYPESAFE_API_KEY=.\+' "$envfile"; then
    log "TYPESAFE_API_KEY set: gate uses rules + Jev combined (GATE_COMBINE=either)"
  else
    log "Jev disabled: gate uses rules only"
  fi

  if grep -q '^OPENAI_API_KEY=.\+' "$envfile"; then
    log "OPENAI_API_KEY set: scoring will use --use-llm (GPT-4o judge)"
  else
    log "no OPENAI_API_KEY: scoring falls back to exact-match"
  fi
}

# --- 7. run agent + benchmark + scoring, modeled on project-log/scripts/run_baseline.sh -
run_and_score() {
  local out="$REPO_ROOT/project-log/runs/$(date +%F)_repro_${PROVIDER}"
  mkdir -p "$out"
  rm -f /tmp/agent_tool_calls.log /tmp/agent_heartbeat.log

  cd "$FDB_V3_DIR"
  echo "start $(date)" > "$out/run.txt"
  echo "agent=$AGENT_SCRIPT provider=$PROVIDER" >> "$out/run.txt"
  echo "gate settings: GATE_COMBINE=$GATE_COMBINE GATE_JEV=$GATE_JEV GATE_DRAFT_HOLD_S=$GATE_DRAFT_HOLD_S GATE_DANGLING=$GATE_DANGLING GATE_PROMPT=$GATE_PROMPT GATE_QUIET_S=$GATE_QUIET_S GATE_HESITANT_QUIET_S=$GATE_HESITANT_QUIET_S GATE_RETRACT=$GATE_RETRACT GATE_ID_NORMALIZE=$GATE_ID_NORMALIZE GATE_BACKCHANNEL=$GATE_BACKCHANNEL GATE_LEAN=$GATE_LEAN GATE_SMART_TURN=$GATE_SMART_TURN (ignored unless AGENT_SCRIPT is gate_agent.py)" >> "$out/run.txt"
  log "starting agent: LK_PROVIDER=$PROVIDER python $AGENT_SCRIPT start"
  LK_PROVIDER="$PROVIDER" python "$AGENT_SCRIPT" start > "$out/agent.log" 2>&1 &
  local agent_pid=$!
  sleep 20

  log "running the 100-recording benchmark"
  python run_tool_benchmark_all_released.py --provider "$PROVIDER" --force > "$out/inference.log" 2>&1
  local rc=$?
  echo "inference exit $rc at $(date)" >> "$out/run.txt"

  kill "$agent_pid" 2>/dev/null || true
  sleep 3
  kill -9 "$agent_pid" 2>/dev/null || true
  cp /tmp/agent_tool_calls.log /tmp/agent_heartbeat.log "$out/" 2>/dev/null || true
  cp "fdb_v3_data_released/evaluation_summary_${PROVIDER}.json" "$out/" 2>/dev/null || true

  bash "$REPO_ROOT/project-log/scripts/score_summary.sh" "$PROVIDER" "$out" | tee "$out/score.txt"
  echo "done $(date)" >> "$out/run.txt"
  log "results in $out"
}

main() {
  install_system_deps
  install_uv
  clone_fdb
  build_env
  fetch_data
  check_env_vars
  run_and_score
}

main "$@"
