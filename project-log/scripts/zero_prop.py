import json, sys
for f in sys.argv[1:]:
    rows = [json.loads(l) for l in open(f)]
    zero = sum(1 for r in rows if not any(e["kind"] == "proposed" for e in r["events"]))
    trans = [sum(1 for e in r["events"] if e["kind"] == "transcript") for r in rows]
    print(f.split("/")[-2][-2:], "rooms", len(rows), "| zero proposals:", zero, "| median transcript events:", sorted(trans)[len(trans)//2])
