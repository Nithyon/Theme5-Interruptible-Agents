#!/usr/bin/env bash
P=$(pgrep -f judge_vertex.py | head -1)
[ -z "$P" ] && { echo "no judge process (finished?)"; exit 0; }
echo "pid $P elapsed $(ps -o etime= -p $P) cpu-time $(ps -o time= -p $P) state $(ps -o stat= -p $P)"
echo "open connections to Google: $(ss -tnp 2>/dev/null | grep "pid=$P," | grep -c ':443')"
sleep 20
echo "cpu-time after 20s: $(ps -o time= -p $P)"
echo "connections now:"; ss -tnp 2>/dev/null | grep "pid=$P," | awk '{print $1, $5}' | head -5
