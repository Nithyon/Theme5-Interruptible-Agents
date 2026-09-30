source ~/theme5/fdb-env/bin/activate
cd /mnt/d/Theme5-Interruptible-Agents/extension
python test_local_fallback.py
python -c "import json;[json.loads(l) for l in open('fallback_eval.jsonl')];print('jsonl ok')"
