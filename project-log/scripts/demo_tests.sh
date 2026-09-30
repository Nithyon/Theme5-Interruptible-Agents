#!/usr/bin/env bash
# Run the recovery layer's automated tests on screen (scripted user, mock devices, no audio).
source ~/theme5/fdb-env/bin/activate
cd /mnt/d/Theme5-Interruptible-Agents/extension
echo "=== Home assistant pack: recovery tests ==="; python test_recovery_home.py
echo; echo "=== In-car pack: recovery tests ==="; python test_recovery.py | tail -12
