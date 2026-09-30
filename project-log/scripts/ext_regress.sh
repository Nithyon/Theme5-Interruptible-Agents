#!/bin/bash
for t in test_recovery test_recovery_home; do
  echo "== $t"; ~/theme5/fdb-env/bin/python /mnt/d/Theme5-Interruptible-Agents/extension/$t.py | tail -3
  ~/theme5/fdb-env/bin/python /mnt/d/Theme5-Interruptible-Agents/extension/$t.py | grep -c '^PASS'
done
