#!/usr/bin/env bash
for p in $(pgrep -f judge_vertex.py); do echo "judge running pid $p, elapsed $(ps -o etime= -p $p)"; done
[ -z "$(pgrep -f judge_vertex.py)" ] && echo "no judge process"
