# Start userspace Ollama only for pulling one model, then stop it.
export OLLAMA_MODELS=~/theme5/ollama/models
export CUDA_VISIBLE_DEVICES=-1
export LD_LIBRARY_PATH=~/theme5/ollama/lib/ollama:${LD_LIBRARY_PATH:-}
if (echo > /dev/tcp/127.0.0.1/11434) 2>/dev/null; then echo "PORT 11434 ALREADY IN USE - abort"; exit 2; fi
nice -n 19 ~/theme5/ollama/bin/ollama serve > ~/theme5/ollama/serve_pull.log 2>&1 &
SP=$!
for i in $(seq 1 30); do (echo > /dev/tcp/127.0.0.1/11434) 2>/dev/null && break; sleep 1; done
MODEL=${1:-functiongemma}
if ! nice -n 19 ~/theme5/ollama/bin/ollama pull "$MODEL" 2>&1 | tr '\r' '\n' | tail -5; then echo PULL_FAILED; fi
~/theme5/ollama/bin/ollama list
kill $SP; wait $SP 2>/dev/null
echo stopped
