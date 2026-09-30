#!/usr/bin/env bash
# Clean-directory test of reproduce.sh steps 1-6 (fresh clone, fresh env, fresh data download).
# Same OS as our dev machine, so system packages (ffmpeg etc.) are already there.
T=~/repro-test; rm -rf "$T"; mkdir -p "$T/Full-Duplex-Bench-tmp"
S=$(date +%s)
export FDB_DIR=$T/Full-Duplex-Bench ENV_DIR=$T/fdb-env SETUP_ONLY=1 UV_NO_CACHE=1
export PATH="$HOME/.local/bin:$PATH"
# the run needs the user's own keys file; stage it where a fresh clone will look (never printed)
( while [ ! -d "$FDB_DIR/v3" ]; do sleep 2; done; cp ~/theme5/Full-Duplex-Bench/v3/.env.local "$FDB_DIR/v3/.env.local" ) &
nice -n 15 bash /mnt/d/Theme5-Interruptible-Agents/reproduce.sh > /tmp/repro_setup.log 2>&1
echo "exit $? after $(( $(date +%s) - S )) s" >> /tmp/repro_setup.log
