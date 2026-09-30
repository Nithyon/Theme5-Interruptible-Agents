#!/usr/bin/env bash
# Read-only: are the 24 "gemini error" hits in the benchmark's agent log real errors or pattern noise?
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-30_full_gate_gemini38_v2
echo "real quota/rate errors (RESOURCE_EXHAUSTED or 'code: 429' / 'status 429'): $(grep -ci 'RESOURCE_EXHAUSTED\|code.\{0,3\}429\|status.\{0,3\}429\|Too Many Requests' $R/agent.log)"
echo "lines with the word quota: $(grep -ci 'quota' $R/agent.log)"
echo "lines with 429 anywhere: $(grep -c '429' $R/agent.log)"
echo "--- sample of what matched (first 3, trimmed):"
grep -i 'resource_exhausted\|quota\|429' $R/agent.log | cut -c1-200 | head -3
echo "--- ERROR-level lines in the benchmark agent log: $(grep -c '"level": "ERROR"' $R/agent.log)"
grep '"level": "ERROR"' $R/agent.log | grep -o '"message": "[^"]\{0,120\}' | sort | uniq -c | head -5
echo "--- demo (talk mode) credential failure:"
tr -d '\n' < /tmp/demo/pre_gate.clean | grep -o 'DefaultCredentialsError[^"\]\{0,220\}\|Your default credentials[^"\]\{0,200\}\|google.auth.exceptions[^"\]\{0,200\}' | head -2
echo "demo env has vertex flag: $(grep -c 'GOOGLE_GENAI_USE_VERTEXAI' /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/demo_gate.sh) (0 = the launch script never loads the settings file)"
echo "leftover talk-mode processes: $(pgrep -fc 'gate_agent.py console\|ext_agent.py console')"
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/run_health.sh | head -4
