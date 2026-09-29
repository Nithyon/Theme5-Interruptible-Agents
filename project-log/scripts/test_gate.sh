#!/usr/bin/env bash
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
python /mnt/d/Theme5-Interruptible-Agents/fdb_agent/test_gate.py 2>&1 | grep -vE "API Backend"
