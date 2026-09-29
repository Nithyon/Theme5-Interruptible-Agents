#!/usr/bin/env bash
# Report on the downloaded FDB-v3 audio without opening any benchmark JSON.
ls -l ~/theme5/downloads
echo "running:"; pgrep -af 'gdown|unzip' | grep -v pgrep || echo "no gdown/unzip running"
python3 - <<'PY'
import zipfile
p = "/home/saini/theme5/downloads/fdb_v3_data_released.zip"
try:
    z = zipfile.ZipFile(p)
    n = z.namelist()
    print("zip ok, entries", len(n), "| input.wav", sum(x.endswith("input.wav") for x in n))
    print("top level:", sorted({x.split("/")[0] for x in n})[:3])
    bad = z.testzip()
    print("crc check:", "all good" if bad is None else f"bad member {bad}")
except Exception as e:
    print("zip not readable:", type(e).__name__, e)
PY
