#!/usr/bin/env bash
# Install Gemini CLI natively in WSL under ~/.npm-global (no sudo), and make it
# win over the Windows copy that WSL sees through /mnt/c.
set -euo pipefail
mkdir -p ~/.npm-global
npm config set prefix ~/.npm-global
LINE='export PATH="$HOME/.npm-global/bin:$PATH"'
grep -qxF "$LINE" ~/.bashrc || echo "$LINE" >> ~/.bashrc
export PATH="$HOME/.npm-global/bin:$PATH"
npm install -g @google/gemini-cli >/tmp/gemini_install.log 2>&1 || { tail -20 /tmp/gemini_install.log; exit 1; }
echo "gemini at: $(command -v gemini)"
gemini --version
