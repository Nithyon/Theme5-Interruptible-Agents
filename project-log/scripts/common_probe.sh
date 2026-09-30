#!/usr/bin/env bash
# Read-only: which files does a recording folder hold (names and sizes only), and how does the scorer find results?
D=~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released
f=$(ls -d $D/*/ | head -1); echo "folder: $(basename $f)"; ls -la $f | awk '{print $5, $9}' | grep -v '^ *$' | head -30
echo "== how evaluate_pass_rate.py walks the results dir (lines mentioning results_dir / glob / walk / listdir):"
grep -n "results_dir\|results-dir\|glob\|os.walk\|listdir\|iterdir\|is_dir\|result_" ~/theme5/Full-Duplex-Bench/v3/evaluate_pass_rate.py | cut -c1-170 | head -30
echo "== scorer log for the symlinked attempt:"; tail -5 /tmp/demo/common_gate_gemini38_v2b.log | cut -c1-200
