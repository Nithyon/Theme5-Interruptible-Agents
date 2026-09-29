#!/usr/bin/env bash
# Show real errors/warnings from an agent log. Usage: agent_errors.sh <agent.log>
L=${1}
echo "rooms joined: $(grep -c 'JOINING' "$L")"
grep -E '"level": "(ERROR|WARNING|CRITICAL)"' "$L" | grep -vE 'event loop blocked|local_track' | cut -c1-500 | tail -8
