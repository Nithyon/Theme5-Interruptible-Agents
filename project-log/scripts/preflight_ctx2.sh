#!/usr/bin/env bash
# Read-only on the talk-mode logs; plus the in-car offline test count (no network, no model).
for n in car home; do
  f=/tmp/demo/pre_$n.clean
  echo "== $n: real credential exceptions=$(grep -c 'DefaultCredentialsError\|could not automatically determine' $f) | function-name mentions=$(grep -c '_get_gcloud_sdk_credentials' $f) | ERROR-level lines=$(grep -c ' ERROR \|\"level\": \"ERROR\"' $f)"
  grep -n ' WARNING \| ERROR ' $f | cut -c1-150 | head -5
  grep -n -B3 '_get_gcloud_sdk_credentials' $f | cut -c1-150 | head -10
done
echo "== in-car offline tests:"
~/theme5/fdb-env/bin/python /mnt/d/Theme5-Interruptible-Agents/extension/test_recovery.py > /tmp/demo/test_recovery.out 2>&1
echo "exit=$? PASS lines=$(grep -c '^PASS' /tmp/demo/test_recovery.out) FAIL lines=$(grep -c '^FAIL' /tmp/demo/test_recovery.out) last: $(tail -1 /tmp/demo/test_recovery.out)"
