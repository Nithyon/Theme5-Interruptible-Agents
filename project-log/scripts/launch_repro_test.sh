#!/usr/bin/env bash
nohup setsid bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/repro_setup_test.sh > /dev/null 2>&1 < /dev/null &
sleep 2; echo started
