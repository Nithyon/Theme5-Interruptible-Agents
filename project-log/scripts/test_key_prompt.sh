#!/usr/bin/env bash
# Test reproduce.sh's key prompt on its own, with made-up values, in a throwaway folder.
# The two functions are lifted out of reproduce.sh and run under a pseudo-terminal.
set -uo pipefail
R=/mnt/d/Theme5-Interruptible-Agents
T=$(mktemp -d)
{
  echo 'set -euo pipefail'
  echo 'log() { echo "[reproduce] $*"; }; die() { echo "[reproduce] ERROR: $*" >&2; exit 1; }'
  echo "FDB_V3_DIR=$T"
  sed -n '/^ask_key() {/,/^}/p;/^prompt_for_keys() {/,/^}/p' "$R/reproduce.sh"
  echo 'prompt_for_keys; echo "rc=$?"'
} > "$T/h.sh"
run() { printf "$1" | script -qec "bash $T/h.sh" /dev/null | tr -d '\r'; }

echo "== case 1: no file, four required keys, skip TypeSafe, give judge key"
run 'wss://demo.livekit.cloud\nFAKEKEY123\nFAKESECRET456\nFAKEGOOGLE789\n\nFAKEOPENAI000\n'
echo "-- file (names and lengths only):"; awk -F= '{print "   " $1 " (" length($2) " chars)"}' "$T/.env.local"
echo "-- permissions: $(stat -c %a "$T/.env.local")"
echo "-- any secret echoed to the terminal above? expect none of FAKE* printed"

echo "== case 2: file complete -> no questions"
run ''
echo "== case 3: one key removed -> asked for that one only, no optional questions"
grep -v '^LIVEKIT_API_SECRET=' "$T/.env.local" > "$T/x" && mv "$T/x" "$T/.env.local"
run 'NEWSECRET999\n'
echo "-- file:"; awk -F= '{print "   " $1 " (" length($2) " chars)"}' "$T/.env.local"
echo "== case 4: required key left empty -> stops"
rm "$T/.env.local"; run '\n'
echo "== case 5: value with a space -> refused"
rm -f "$T/.env.local"; run 'wss://demo.livekit.cloud\nbad key\n'
echo "== case 6: not a terminal (pipe) -> no questions"
echo x | bash "$T/h.sh"
echo "== syntax check of the whole script: $(bash -n "$R/reproduce.sh" && echo ok)"
rm -rf "$T"
