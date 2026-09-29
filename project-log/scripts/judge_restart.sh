#!/usr/bin/env bash
pkill -f judge_vertex.py; pkill -f judge_score.sh; sleep 2
echo "stopped: $(pgrep -fc judge_vertex.py) left"
