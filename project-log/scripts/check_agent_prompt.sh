#!/usr/bin/env bash
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
python - <<'PY' 2>&1 | grep -v 'API Backend'
import sys; sys.path.insert(0, "/mnt/d/Theme5-Interruptible-Agents/fdb_agent"); sys.path.insert(0, ".")
import os
os.environ["GATE_PROMPT"] = "1"
import gate_agent as g
a = g.GatedVoiceAgent()
print("prompt has rules:", "RULES FOR THIS CALL" in a.instructions, "| length", len(a.instructions))
os.environ["GATE_PROMPT"] = "0"
print("prompt off:", "RULES FOR THIS CALL" not in g.GatedVoiceAgent().instructions)
from gate import classify_followup as c
for t in ["", "no sorry New York", "and also order B2", "the blue one", "actually make it three"]:
    print(repr(t), "->", c(t))
PY
