#!/usr/bin/env bash
# Optional: reproduce the use-case extension (in-car EV assistant, Bixby-style home assistant,
# local Gemma fallback). Separate from ./reproduce.sh, which reproduces the benchmark score.
#
# Usage:
#   ./reproduce_extension.sh [tests]           offline tests of the recovery layer, MCP plugin and
#                                              fallback (no keys, no GPU; needs python3 and uv)
#   ./reproduce_extension.sh fallback [args]   local fallback suite on Ollama (no keys). Needs Ollama
#                                              running and the model pulled; extra args go to
#                                              extension/fallback_suite.py (e.g. --limit 5 --sets own)
#   ./reproduce_extension.sh e2e [car|home|slurp|slurp_pauses]
#                                              extension agent end to end on a recorded clip through
#                                              LiveKit (needs the setup and keys of ./reproduce.sh:
#                                              run `SETUP_ONLY=1 ./reproduce.sh` first)
#   ./reproduce_extension.sh all               tests, then fallback if Ollama is up, then e2e car if
#                                              the benchmark setup exists; skipped parts say why
#
# Settings (all optional):
#   EXT_ENV_DIR     venv for the offline tests            (default ~/theme5/ext-env)
#   OLLAMA_URL      Ollama server                         (default http://127.0.0.1:11434)
#   FALLBACK_MODEL  model for the fallback suite          (default gemma4:26b-a4b-it-qat, ~16 GB)
#   FALLBACK_RUNS   runs of each command set              (default 1)
#   FDB_DIR/ENV_DIR same meaning and defaults as in ./reproduce.sh
#
# Keys are never asked for, read or printed here: e2e only checks that the variable NAMES exist
# in $FDB_V3_DIR/.env.local. Does not touch /tmp/agent_tool_calls.log or the benchmark's logs.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_ENV_DIR="${EXT_ENV_DIR:-$HOME/theme5/ext-env}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
FALLBACK_MODEL="${FALLBACK_MODEL:-gemma4:26b-a4b-it-qat}"
FALLBACK_RUNS="${FALLBACK_RUNS:-1}"
FDB_DIR="${FDB_DIR:-$HOME/theme5/Full-Duplex-Bench}"
FDB_V3_DIR="$FDB_DIR/v3"
ENV_DIR="${ENV_DIR:-$HOME/theme5/fdb-env}"

log() { echo "[extension] $*"; }
die() { echo "[extension] ERROR: $*" >&2; exit 1; }

# --- tests: offline, no keys ------------------------------------------------------------
build_test_env() {
  command -v uv >/dev/null 2>&1 || die "uv not found; install it (https://docs.astral.sh/uv/) or run ./reproduce.sh once"
  if [ ! -x "$EXT_ENV_DIR/bin/python" ]; then
    log "creating test venv at $EXT_ENV_DIR"
    uv venv -q --python 3.12 "$EXT_ENV_DIR" || uv venv -q "$EXT_ENV_DIR"
  fi
  # mcp<2: mcp 2.x renamed FastMCP, which test_mcp_plugin.py imports.
  VIRTUAL_ENV="$EXT_ENV_DIR" uv pip install -q requests "mcp<2"
}

run_tests() {
  build_test_env
  local py="$EXT_ENV_DIR/bin/python" failed=0 t n
  cd "$REPO_ROOT"
  for t in test_recovery test_recovery_home test_mcp_plugin test_local_fallback; do
    if out="$("$py" "extension/$t.py" 2>&1)"; then
      n=$(grep -c '^PASS' <<<"$out" || true)
      log "$t: ALL PASS ($n checks)"
    else
      failed=1
      log "$t: FAILED"; grep -E '^FAIL|Error|Traceback' <<<"$out" | head -5 | sed 's/^/    /'
    fi
  done
  [ "$failed" -eq 0 ] || die "some extension tests failed (details above)"
  log "offline tests: all passed"
}

# --- fallback: local model on Ollama, no keys --------------------------------------------
ollama_up() { curl -sf -m 5 "$OLLAMA_URL/api/version" >/dev/null 2>&1; }

run_fallback() {
  ollama_up || die "no Ollama server at $OLLAMA_URL; start it with 'ollama serve' (or set OLLAMA_URL)"
  curl -sf -m 10 "$OLLAMA_URL/api/tags" | grep -qE "\"$FALLBACK_MODEL(:latest)?\"" || \
    die "model $FALLBACK_MODEL is not pulled; run: ollama pull $FALLBACK_MODEL  (not done automatically; the default model is ~16 GB)"
  build_test_env
  local tag out
  tag="$(sed 's/[^A-Za-z0-9._-]\+/_/g' <<<"$FALLBACK_MODEL")"
  out="$REPO_ROOT/project-log/runs/$(date +%F)_fallback_suite_$tag"
  [ ! -e "$out" ] || die "$out already exists; move it aside first so earlier results are not overwritten"
  log "fallback suite: model $FALLBACK_MODEL, $FALLBACK_RUNS run(s), extra args: ${*:-none}"
  log "about 6 s per command for the default model on a 32 GB laptop; keep the machine otherwise idle"
  cd "$REPO_ROOT"
  "$EXT_ENV_DIR/bin/python" extension/fallback_suite.py --model "$FALLBACK_MODEL" --url "$OLLAMA_URL" \
    --runs "$FALLBACK_RUNS" --timeout 30 "$@"
  log "results in $out (summary.md has the table)"
}

# --- e2e: extension agent on a recorded clip through LiveKit ------------------------------
bench_ready() {
  [ -x "$ENV_DIR/bin/python" ] && [ -f "$FDB_V3_DIR/run_tool_benchmark_all_released.py" ] && [ -f "$FDB_V3_DIR/.env.local" ]
}

check_keys() {
  local envfile="$FDB_V3_DIR/.env.local" v missing=()
  for v in LIVEKIT_URL LIVEKIT_API_KEY LIVEKIT_API_SECRET; do
    grep -q "^${v}=.\+" "$envfile" || missing+=("$v")
  done
  grep -q '^GOOGLE_API_KEY=.\+' "$envfile" || grep -q '^GOOGLE_GENAI_USE_VERTEXAI=true' "$envfile" || \
    missing+=("GOOGLE_API_KEY (or GOOGLE_GENAI_USE_VERTEXAI)")
  [ "${#missing[@]}" -eq 0 ] || die "missing in $envfile (names only): ${missing[*]}; run ./reproduce.sh in a terminal to be asked for them"
  log "LiveKit and Gemini variables present (names checked only)"
}

run_e2e() {
  local pack="${1:-car}" clip ext_pack fail_first=0
  case "$pack" in
    car)          clip=audio_car;          ext_pack=car ;;
    home)         clip=audio;              ext_pack=home ;;
    slurp)        clip=audio_slurp;        ext_pack=home; fail_first=1 ;;
    slurp_pauses) clip=audio_slurp_pauses; ext_pack=home; fail_first=1 ;;
    *) die "unknown e2e pack '$pack' (car, home, slurp or slurp_pauses)" ;;
  esac
  bench_ready || die "benchmark setup not found (ENV_DIR=$ENV_DIR, FDB_DIR=$FDB_DIR); run: SETUP_ONLY=1 ./reproduce.sh"
  check_keys

  local provider="repro_ext_$pack" audio="$REPO_ROOT/extension/e2e/$clip"
  local out="$REPO_ROOT/project-log/runs/$(date +%F)_repro_ext_$pack"
  local events="/tmp/repro_ext_${pack}_events.log"
  [ -d "$audio" ] || die "clip folder $audio missing"
  mkdir -p "$out"; rm -f "$events"
  # shellcheck disable=SC1091
  source "$ENV_DIR/bin/activate"
  cd "$FDB_V3_DIR"
  set -a; # shellcheck disable=SC1091
  source .env.local; set +a
  {
    echo "start $(date)"
    echo "EXT_PACK=$ext_pack EXT_SEED=0 EXT_LIGHTS_FAIL_FIRST=$fail_first provider=$provider clip=$(ls "$audio")"
  } > "$out/run.txt"

  log "starting extension agent ($pack)"
  EXT_EVENT_LOG="$events" EXT_LIGHTS_FAIL_FIRST="$fail_first" EXT_PACK="$ext_pack" EXT_SEED=0 \
    LK_PROVIDER="$provider" python "$REPO_ROOT/extension/ext_agent.py" start > "$out/agent.log" 2>&1 &
  local agent_pid=$! rc=0
  sleep 20
  log "streaming the recorded clip with the benchmark's runner"
  python run_tool_benchmark_all_released.py --provider "$provider" --root_dir "$audio" --force \
    > "$out/inference.log" 2>&1 || rc=$?
  echo "inference exit $rc at $(date)" >> "$out/run.txt"
  sleep 6; kill "$agent_pid" 2>/dev/null || true; sleep 4; kill -9 "$agent_pid" 2>/dev/null || true

  cp "$events" "$out/ext_recovery_events.log" 2>/dev/null || true
  local f; f="$(ls -d "$audio"/*/ | head -1)"
  cp "${f}result_$provider.json" "$out/result.json" 2>/dev/null || true
  cp "${f}output_$provider.wav" "$out/agent_reply.wav" 2>/dev/null || true
  python - "$out" <<'PY'
import json, os, sys
o = sys.argv[1]
p = os.path.join(o, "result.json")
if os.path.exists(p):
    r = json.load(open(p)); print("status:", r.get("status")); print("agent said:", (r.get("transcript") or "")[:700])
else:
    print("no result file; see agent.log and inference.log")
p = os.path.join(o, "ext_recovery_events.log")
if os.path.exists(p):
    print("recovery events:")
    for line in open(p):
        try: e = json.loads(line)
        except ValueError: continue
        print("  ", e.get("kind"), {k: v for k, v in e.items() if k not in ("kind", "seq", "t", "ts") and v not in (None, "", {}, [])})
PY
  log "results in $out"
}

main() {
  local mode="${1:-tests}"; [ $# -gt 0 ] && shift
  case "$mode" in
    tests)    run_tests ;;
    fallback) run_fallback "$@" ;;
    e2e)      run_e2e "$@" ;;
    all)
      run_tests
      if ollama_up; then (run_fallback) || log "fallback suite did not complete (see above)"
      else log "skipping fallback: no Ollama server at $OLLAMA_URL"; fi
      if bench_ready; then (run_e2e car) || log "e2e car did not complete (see above)"
      else log "skipping e2e: benchmark setup not found (run SETUP_ONLY=1 ./reproduce.sh first)"; fi
      ;;
    -h|--help|help) sed -n '2,26p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//' ;;
    *) die "unknown mode '$mode' (tests, fallback, e2e, all; --help for details)" ;;
  esac
}

main "$@"
