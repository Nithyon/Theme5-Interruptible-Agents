# Userspace Ollama install (no sudo). Rate-limited + niced. Current release asset is .tar.zst.
set -u
mkdir -p ~/theme5/ollama && cd ~/theme5/ollama
if [ ! -f ollama-linux-amd64.tar.zst ]; then
  nice -n 19 curl -L --fail --limit-rate 3M -o ollama-linux-amd64.tar.zst https://ollama.com/download/ollama-linux-amd64.tar.zst || { echo DL_FAILED; exit 1; }
fi
ls -l ollama-linux-amd64.tar.zst
which zstd unzstd bsdtar; ls ~/theme5/localdeb | head
