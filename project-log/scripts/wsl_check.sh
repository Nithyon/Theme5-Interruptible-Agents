#!/usr/bin/env bash
# Clone (from the local Windows mirror) and report what the WSL environment has.
cd ~ && mkdir -p theme5 && cd theme5
if [ ! -d Full-Duplex-Bench/.git ]; then
  rm -rf Full-Duplex-Bench
  git clone /mnt/d/Theme5-FDB-mirror.git Full-Duplex-Bench 2>&1 | tail -1
  git -C Full-Duplex-Bench remote set-url origin https://github.com/DanielLin94144/Full-Duplex-Bench.git
fi
echo "--- repo:"; ls Full-Duplex-Bench
echo "--- v3:"; ls Full-Duplex-Bench/v3
echo "--- tools:"
for t in git python3 conda pip3 ffmpeg nvidia-smi; do printf '%-11s ' "$t"; command -v "$t" || echo MISSING; done
python3 --version
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>&1 | head -1
echo "--- disk:"; df -h ~ | tail -1
echo "--- dns:"; grep -v '^#' /etc/resolv.conf; cat /etc/wsl.conf 2>/dev/null
echo "--- net:"; getent hosts github.com || echo "cannot resolve github.com"
