#!/usr/bin/env bash
# Is practice run E alive, and do the demo agents at least import and show their CLI?
echo "running: $(pgrep -fc 'gate_agent.py|livekit_inference')"; tail -2 /tmp/dev_e.out
source ~/theme5/fdb-env/bin/activate; cd ~/theme5/Full-Duplex-Bench/v3
set -a; source .env.local 2>/dev/null; set +a
echo "== ext_agent import"; LK_PROVIDER=ext_gemini38 timeout 40 python /mnt/d/Theme5-Interruptible-Agents/extension/ext_agent.py --help 2>&1 | tail -15
echo "== audio devices"; python - <<'PY'
try:
    import sounddevice as sd
    print(sd.query_devices())
except Exception as e:
    print("sounddevice:", type(e).__name__, e)
PY
ls /mnt/wslg 2>/dev/null | head -5; echo "PULSE_SERVER=$PULSE_SERVER"
