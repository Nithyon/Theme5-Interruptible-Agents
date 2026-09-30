#!/usr/bin/env bash
# Quick check that extension/fallback_suite.py runs: userspace Ollama on a side port (11500, so it
# cannot collide with another Ollama on 11434), the small functiongemma model, a few commands.
# Usage: fallback_suite_smoke.sh [extra args for fallback_suite.py, e.g. --limit 6 --runs 2]
export OLLAMA_MODELS=~/theme5/ollama/models OLLAMA_NUM_PARALLEL=1 OLLAMA_KEEP_ALIVE=5m OLLAMA_HOST=127.0.0.1:11500
export LD_LIBRARY_PATH=~/theme5/ollama/lib/ollama:${LD_LIBRARY_PATH:-}
export CUDA_VISIBLE_DEVICES=-1
~/theme5/ollama/bin/ollama serve > ~/theme5/ollama/serve_suite.log 2>&1 &
SP=$!
trap 'kill $SP 2>/dev/null; wait $SP 2>/dev/null; echo "ollama stopped"' EXIT
for i in $(seq 1 60); do (echo > /dev/tcp/127.0.0.1/11500) 2>/dev/null && break; sleep 1; done
source ~/theme5/fdb-env/bin/activate
cd /mnt/d/Theme5-Interruptible-Agents
python extension/make_fallback_slurp.py ~/theme5/slurp/test-00000.parquet
python extension/fallback_suite.py --model functiongemma --url http://127.0.0.1:11500 "$@" 2>&1 | tail -25
