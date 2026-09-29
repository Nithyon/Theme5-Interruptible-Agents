#!/usr/bin/env bash
# Build the FDB-v3 Python environment in WSL (user level, no sudo).
# Python 3.10 via uv (the FDB README uses conda python=3.10; uv avoids the
# Anaconda terms-of-service prompt). PyTorch is the CUDA 12.8 build because the
# RTX 5070 (Blackwell) needs CUDA 12.8 or newer.
# Usage: bash setup_fdb_env.sh   (log: ~/theme5/setup_fdb_env.log)
set -euo pipefail
FDB=~/theme5/Full-Duplex-Bench/v3
ENV=~/theme5/fdb-env

if ! command -v uv >/dev/null 2>&1 && [ ! -x ~/.local/bin/uv ]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"
uv --version

[ -d "$ENV" ] || uv venv --python 3.10 "$ENV"
source "$ENV/bin/activate"
python --version

echo "=== torch (cu128)"
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128

echo "=== FDB-v3 requirements (from v3/README.md)"
uv pip install "livekit-agents[openai,google,xai]~=1.3" \
  "livekit-plugins-ultravox" "livekit-plugins-silero" "livekit-plugins-openai" \
  "livekit[crypto]~=1.0" python-dotenv numpy "nemo_toolkit[asr]" pydub ffmpeg-python openai

echo "=== checks"
python - <<'PY'
import torch
print("torch", torch.__version__, "cuda build", torch.version.cuda)
print("cuda available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("gpu:", torch.cuda.get_device_name(0))
    x = torch.ones(1024, 1024, device="cuda"); print("gpu matmul ok:", float((x @ x).sum()) > 0)
import livekit.agents, nemo
print("livekit-agents", livekit.agents.__version__, "| nemo", nemo.__version__)
PY
command -v ffmpeg && ffmpeg -version | head -1 || echo "ffmpeg MISSING"
uv pip freeze > ~/theme5/env-freeze.txt
echo "=== done; freeze at ~/theme5/env-freeze.txt"
