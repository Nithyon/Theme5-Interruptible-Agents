#!/usr/bin/env bash
# Extract the FDB-v3 audio into v3/ (skipping macOS metadata) and count it.
set -euo pipefail
cd ~/theme5/Full-Duplex-Bench/v3
python3 - <<'PY'
import zipfile
z = zipfile.ZipFile("/home/saini/theme5/downloads/fdb_v3_data_released.zip")
members = [m for m in z.namelist() if not m.startswith("__MACOSX")]
z.extractall(".", members=members)
print("extracted", len(members), "entries")
PY
echo "folders: $(find fdb_v3_data_released -mindepth 1 -maxdepth 1 -type d | wc -l)"
echo "input.wav: $(find fdb_v3_data_released -name input.wav | wc -l)"
echo "folders missing input.wav: $(for d in fdb_v3_data_released/*/; do [ -f "$d/input.wav" ] || echo "$d"; done | wc -l)"
du -sh fdb_v3_data_released
