#!/usr/bin/env bash
# Fetch one shard of the SLURP test split (real recordings) from a Hugging Face mirror of the
# dataset. SLURP: Bastianelli et al., EMNLP 2020; audio licence CC BY-NC 4.0. Kept outside the repo.
set -uo pipefail
mkdir -p ~/theme5/slurp && cd ~/theme5/slurp
URL=https://huggingface.co/datasets/marcel-gohsen/slurp/resolve/main/data/test-00000-of-00002.parquet
curl -L --fail -C - -o test-00000.parquet "$URL" 2> curl.log
echo "exit $? size $(stat -c %s test-00000.parquet 2>/dev/null)"
