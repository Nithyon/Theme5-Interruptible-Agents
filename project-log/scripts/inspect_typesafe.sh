#!/usr/bin/env bash
~/.local/bin/uv pip install --python ~/theme5/fdb-env/bin/python typesafe-sdk==0.7.2 2>&1 | tail -2
source ~/theme5/fdb-env/bin/activate
python - <<'PY'
import inspect, typesafe_sdk as t
print("exports:", [n for n in dir(t) if not n.startswith("_")])
C = t.TypeSafeClient
print("system_one:", inspect.signature(C.system_one))
A = getattr(t, "AsyncTypeSafeClient", None)
print("async client:", A, inspect.signature(A.system_one) if A else "")
print("Choice:", inspect.signature(t.Choice))
PY
P=$(python -c 'import typesafe_sdk,os;print(os.path.dirname(typesafe_sdk.__file__))')
grep -rnE 'class .*(Response|ChoiceResult|Answer)|probabilit|confidence|timeout' $P/*.py | head -20
