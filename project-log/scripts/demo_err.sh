#!/usr/bin/env bash
date '+%H:%M UTC-now'
sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' /tmp/demo_start.log | grep -n "ERROR\|Error\|error\|raise \|Exception" | grep -v DEBUG | cut -c1-400 | head -20
