#!/usr/bin/env bash
# After editing the extension agent: offline tests and an import check for both packs (no agent is started).
source ~/theme5/fdb-env/bin/activate
cd /mnt/d/Theme5-Interruptible-Agents/extension
for t in test_recovery.py test_recovery_home.py; do o=$(python $t 2>&1); echo "$t: PASS $(echo "$o" | grep -c '^PASS') FAIL $(echo "$o" | grep -c '^FAIL') | $(echo "$o" | tail -1)"; done
cd ~/theme5/Full-Duplex-Bench/v3
for p in car home; do EXT_PACK=$p timeout 60 python /mnt/d/Theme5-Interruptible-Agents/extension/ext_agent.py --help > /tmp/demo/ext_help_$p.log 2>&1; echo "import check $p: exit $? ($(grep -c 'Commands' /tmp/demo/ext_help_$p.log) help screen)"; done
