#!/usr/bin/env bash
# Read-only: what is the one traceback in the talk-mode log, and what is the gemini-realtime-session line?
f=/tmp/demo/pre_gate.clean
echo "--- Traceback and the 8 lines after it:"
grep -n -A8 'Traceback' $f | cut -c1-170 | head -14
echo "--- message of the line mentioning gemini-realtime-session:"
grep -n -B6 'gemini-realtime-session' $f | cut -c1-170 | head -12
echo "--- WARNING/ERROR level lines (not debug):"
grep -n ' WARNING \| ERROR \|"level": "WARNING"\|"level": "ERROR"' $f | cut -c1-170 | head -8
