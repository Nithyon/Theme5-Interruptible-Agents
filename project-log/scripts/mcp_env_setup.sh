#!/bin/bash
# Create the separate MCP test env (never touches ~/theme5/fdb-env).
set -e
UV=$(command -v uv || echo ~/.local/bin/uv)
[ -d ~/theme5/mcp-env ] || nice -n 15 "$UV" venv --python 3.10 ~/theme5/mcp-env
VIRTUAL_ENV=~/theme5/mcp-env nice -n 15 "$UV" pip install "mcp<2"
~/theme5/mcp-env/bin/python -c "import mcp,importlib.metadata as m;print('mcp',m.version('mcp'))"
