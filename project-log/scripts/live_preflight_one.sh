#!/usr/bin/env bash
# Start ONE demo agent in talk mode for ~35 s (nobody speaking), low priority, and report.
# Usage: live_preflight_one.sh gate | car | home
S=/mnt/d/Theme5-Interruptible-Agents/project-log/scripts; n=${1:?which}; mkdir -p /tmp/demo
case $n in gate) cmd="bash $S/demo_gate.sh";; car) cmd="bash $S/demo_car.sh car";; home) cmd="bash $S/demo_car.sh home";; esac
timeout 35 nice -n 10 $cmd < /dev/null > /tmp/demo/pre_$n.log 2>&1
f=/tmp/demo/pre_$n.clean; sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' /tmp/demo/pre_$n.log > $f
echo "== $n: job crashed=$(grep -c 'job crashed' $f) tracebacks=$(grep -c 'Traceback' $f) (1 expected: no keyboard attached) credential errors=$(grep -ci 'DefaultCredentialsError\|_get_gcloud_sdk_credentials\|could not automatically determine' $f) unhandled=$(grep -c 'unhandled exception' $f)"
tr -d '\n' < $f | grep -o '[A-Za-z_.]*\(Error\|Exception\): [^"\]\{0,160\}' | grep -v termios | sort | uniq -c | head -4
grep -i 'gemini\|realtime' $f | grep -vi 'debug' | cut -c1-150 | head -4
echo "lines in log: $(wc -l < $f)"
