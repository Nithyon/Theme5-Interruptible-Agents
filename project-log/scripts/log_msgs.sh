#!/usr/bin/env bash
# Most common non-routine agent log messages. Usage: log_msgs.sh <agent.log>
grep -oE '"message": "[^"]{0,110}' "$1" \
 | grep -viE 'process initialized|initializing process|received job|RoomIO|closing agent session|LATENCY|process exiting|publisher data|pass-through|provided project' \
 | sed 's/[0-9a-f]\{8,\}//g' | sort | uniq -c | sort -rn | head -15
