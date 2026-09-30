#!/usr/bin/env bash
date '+%H:%M UTC'
echo "done: $(find ~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released -name 'result_gate_gemini38_v2.json' | wc -l)"
