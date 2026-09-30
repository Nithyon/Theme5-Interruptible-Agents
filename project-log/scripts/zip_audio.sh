#!/usr/bin/env bash
# Zip the agent's recorded audio per run (for Drive; too big for git).
python3 - <<'PY'
import glob, os, zipfile
D=os.path.expanduser("~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released")
A="/mnt/d/Theme5-Interruptible-Agents/logs-audio"; os.makedirs(A, exist_ok=True)
for p in ("gemini3_8","gate_gemini38_final"):
    files=sorted(glob.glob(f"{D}/*/output_{p}.wav"))
    out=f"{A}/agent_audio_{p}.zip"
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for f in files: z.write(f, os.path.relpath(f, D))
    print(p, len(files), "files", round(os.path.getsize(out)/1e6), "MB")
PY
