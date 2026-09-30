#!/usr/bin/env bash
# Run the local-fallback offline tests (fake model, no inference) and count results.
o=$(~/theme5/fdb-env/bin/python /mnt/d/Theme5-Interruptible-Agents/extension/test_local_fallback.py 2>&1)
echo "exit=$? PASS=$(echo "$o" | grep -c '^PASS') FAIL=$(echo "$o" | grep -c '^FAIL')"
echo "$o" | grep -v '^PASS' | head -5
