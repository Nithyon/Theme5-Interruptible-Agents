#!/usr/bin/env bash
# Start each demo agent in talk (console) mode for ~35 s without anyone speaking, one at a
# time and at low priority, and report whether it came up cleanly. Logs go to /tmp/demo only.
S=/mnt/d/Theme5-Interruptible-Agents/project-log/scripts
mkdir -p /tmp/demo
one() {   # name, command...
  local n=$1; shift
  timeout 35 nice -n 10 "$@" < /dev/null > /tmp/demo/pre_$n.log 2>&1
  local f=/tmp/demo/pre_$n.clean
  sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' /tmp/demo/pre_$n.log > $f
  echo "== $n: crashed=$(grep -c 'job crashed' $f) plugin_err=$(grep -c 'Plugins must be registered' $f) tracebacks=$(grep -c 'Traceback' $f) gemini_err=$(grep -ci 'permission_denied\|unauthenticated\|quota\|RESOURCE_EXHAUSTED' $f)"
  grep -i 'error' $f | grep -vi 'termios\|DEBUG\|error_handling' | cut -c1-220 | head -4
  grep -i 'realtime\|session started\|connected\|speaking\|listening' $f | grep -vi debug | cut -c1-160 | head -5
}
one gate bash $S/demo_gate.sh
one car  bash $S/demo_car.sh car
one home bash $S/demo_car.sh home
echo "== benchmark after preflight:"; bash $S/run_health.sh
