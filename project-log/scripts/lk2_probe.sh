#!/usr/bin/env bash
# Read-only: names in lk2.env (no values), and how env, ports, /tmp logs and resume work.
echo "lk2.env names: $(grep -o '^[A-Z_0-9]*=' ~/theme5/lk2.env | tr '\n' ' ')  lines: $(grep -c . ~/theme5/lk2.env)"
echo "same URL as main? $( [ "$(grep '^LIVEKIT_URL=' ~/theme5/lk2.env)" = "$(grep '^LIVEKIT_URL=' ~/theme5/Full-Duplex-Bench/v3/.env.local)" ] && echo YES-SAME || echo different)"
cd ~/theme5/Full-Duplex-Bench/v3
echo "== dotenv / tmp / port usage"
grep -n "load_dotenv\|/tmp/\|8081\|port=" lk_agent_tool.py livekit_inference.py run_tool_benchmark_all_released.py run_tool_benchmark.py /mnt/d/Theme5-Interruptible-Agents/fdb_agent/gate_agent.py /mnt/d/Theme5-Interruptible-Agents/fdb_agent/models.py | cut -c1-200
echo "== force / skip logic"
grep -n "force\|exists" run_tool_benchmark_all_released.py | cut -c1-200 | head -30
