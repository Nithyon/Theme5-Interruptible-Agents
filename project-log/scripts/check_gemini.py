"""Check the Gemini key in v3/.env.local works and which Live models it can use.
Listing models is free; prints no secrets."""
from pathlib import Path
from dotenv import dotenv_values
from google import genai

key = (dotenv_values(Path.home() / "theme5/Full-Duplex-Bench/v3/.env.local").get("GOOGLE_API_KEY") or "").strip()
if not key:
    raise SystemExit("GOOGLE_API_KEY missing")
print("key format:", "AIza…" if key.startswith("AIza") else key[:3] + "… (not the usual AIza format)")
try:
    client = genai.Client(api_key=key)
    names = [m.name.split("/")[-1] for m in client.models.list()]
except Exception as e:
    msg = str(e).replace(key, "***")
    raise SystemExit(f"Gemini key REJECTED: {type(e).__name__}: {msg[:200]}")
print("Gemini key OK,", len(names), "models visible")
for n in sorted(names):
    if "live" in n or "native-audio" in n:
        print("  live/audio model:", n)
