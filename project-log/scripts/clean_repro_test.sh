#!/usr/bin/env bash
# Clean-folder test of reproduce.sh: steps 1-6 only (no run), into fresh directories, so the
# install path is exercised from nothing. The existing ~/theme5 environment is not touched.
T=~/theme5/clean_test_$(date +%H%M)
mkdir -p "$T"
cd /mnt/d/Theme5-Interruptible-Agents
echo "clean dir: $T  start $(date -u)"
SETUP_ONLY=1 FDB_DIR="$T/Full-Duplex-Bench" ENV_DIR="$T/fdb-env" bash ./reproduce.sh > "$T/reproduce.log" 2>&1
RC=$?
echo "exit $RC  end $(date -u)"
echo "--- last 40 lines"; tail -40 "$T/reproduce.log"
echo "--- env: $(ls "$T/fdb-env/bin/python" 2>&1)"
[ -x "$T/fdb-env/bin/python" ] && "$T/fdb-env/bin/python" -c "import livekit.agents, torch; print('livekit-agents', livekit.agents.__version__, 'torch', torch.__version__)" 2>&1 | tail -2
echo "--- benchmark data folders: $(ls -d "$T"/Full-Duplex-Bench/v3/*/ 2>/dev/null | wc -l)"
