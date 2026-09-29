"""Why did dev-set scenarios fail? (our own practice data; fine to inspect)"""
import json, pathlib, sys
L = sys.argv[1]; ids = sys.argv[2].split(",")
D = pathlib.Path("/mnt/d/Theme5-Interruptible-Agents/devset")
sc = {json.loads(l)["id"]: json.loads(l) for l in open(D / "scenarios.jsonl") if l.strip()}
for f in sorted((D / "audio").glob(f"*/result_dev_gate_gemini38_{L}.json")):
    sid = f.parent.name.split("_")[0]
    if sid not in ids: continue
    r = json.load(open(f)); s = sc[sid]
    print(f"== {sid} [{','.join(s['disfluency'])}]  said: {s['utterance'][:110]}")
    print("   expected:", [(c['name'], c['args']) for c in s['expected_calls']])
    print("   actual:  ", [(c.get('function'), c.get('arguments') or c.get('args')) for c in r.get('actual_tool_calls', [])])
    print("   agent:   ", (r.get('transcript') or '')[:140].replace('\n', ' '))
