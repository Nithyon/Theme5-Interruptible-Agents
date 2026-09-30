"""Shape check of ~/theme5/lk2.env without printing any value."""
from pathlib import Path
from dotenv import dotenv_values
a = dotenv_values(Path.home() / "theme5/lk2.env")
b = dotenv_values(Path.home() / "theme5/Full-Duplex-Bench/v3/.env.local")
def bad(v):
    return v != v.strip() or ' ' in v or chr(34) in v


for k in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"):
    v, w = (a.get(k) or ""), (b.get(k) or "")
    print(f"{k:20s} len {len(v):3d} (working one: {len(w)})  same as main project: {v == w}  "
          f"spaces/quotes: {bad(v)}  "
          + (f"starts with 'API': {v.startswith('API')} (working: {w.startswith('API')})" if k == "LIVEKIT_API_KEY" else "")
          + (f"ends .livekit.cloud: {v.rstrip('/').endswith('.livekit.cloud')}" if k == "LIVEKIT_URL" else ""))
raw = (Path.home() / "theme5/lk2.env").read_bytes()
print("CRLF line endings:", b"\r" in raw)
