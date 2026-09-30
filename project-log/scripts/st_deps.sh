#!/usr/bin/env bash
source ~/theme5/fdb-env/bin/activate
python - <<'PY'
for m in ("onnxruntime","transformers","numpy","huggingface_hub"):
    try:
        mod=__import__(m); print(m, mod.__version__)
    except Exception as e:
        print(m, "MISSING", type(e).__name__)
PY
nproc; ls ~/theme5/models 2>/dev/null
