#!/usr/bin/env bash
source ~/theme5/fdb-env/bin/activate
python - <<'PY'
from google import genai
c = genai.Client(vertexai=True, project="hackathon-cinemahackathon", location="global")
names = sorted(m.name.split("/")[-1] for m in c.models.list())
print("pro models:", [n for n in names if "pro" in n])
PY
cd ~/theme5/Full-Duplex-Bench/v3
echo "=== judge calls in the scorers"
sed -n '86,135p' evaluate_pass_rate.py
echo "=== evaluate_tool_calls judge"
sed -n '75,175p' evaluate_tool_calls.py | grep -nE 'def |create\(|model=|max_tokens|content|strip|upper|json|YES|NO|score' | head -30
grep -nE '^from evaluate_tool_calls|^import evaluate_tool_calls|evaluate_tool_calls\.' evaluate_pass_rate.py | head
