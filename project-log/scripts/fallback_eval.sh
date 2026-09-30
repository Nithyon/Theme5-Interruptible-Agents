#!/usr/bin/env bash
# One command: start userspace Ollama, run the offline-fallback eval, stop Ollama.
# Run ONLY when no benchmark is running (it does local model inference).
# Usage (from PowerShell): wsl -d Ubuntu bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/fallback_eval.sh [--limit N]
export OLLAMA_MODELS=~/theme5/ollama/models
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_KEEP_ALIVE=5m
export LD_LIBRARY_PATH=~/theme5/ollama/lib/ollama:${LD_LIBRARY_PATH:-}
export CUDA_VISIBLE_DEVICES=-1   # CPU only; remove this line to let Ollama use the GPU
if (echo > /dev/tcp/127.0.0.1/11434) 2>/dev/null; then echo "port 11434 already in use; aborting"; exit 2; fi

~/theme5/ollama/bin/ollama serve > ~/theme5/ollama/serve_eval.log 2>&1 &
SP=$!
trap 'kill $SP 2>/dev/null; wait $SP 2>/dev/null; echo "ollama stopped"' EXIT
for i in $(seq 1 60); do (echo > /dev/tcp/127.0.0.1/11434) 2>/dev/null && break; sleep 1; done
(echo > /dev/tcp/127.0.0.1/11434) 2>/dev/null || { echo "ollama did not start; see ~/theme5/ollama/serve_eval.log"; exit 1; }

source ~/theme5/fdb-env/bin/activate
cd /mnt/d/Theme5-Interruptible-Agents/extension
# warm-up so model load time is not counted in per-request latency
curl -s http://127.0.0.1:11434/api/chat -d '{"model":"functiongemma","messages":[{"role":"user","content":"hi"}],"stream":false}' > /dev/null
python eval_fallback.py "$@"
