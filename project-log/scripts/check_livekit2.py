"""Check v3/.env.local and LiveKit connectivity without printing any secret.

Run in WSL:  ~/theme5/fdb-env/bin/python /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/check_livekit.py
Prints which variable names are set (never values), then joins and leaves an empty
LiveKit room to prove the URL/key/secret work. Free: a few seconds of connection time.
"""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import dotenv_values

ENV = Path(os.getenv("LK_ENV_FILE") or (Path.home() / "theme5/Full-Duplex-Bench/v3/.env.local"))
WANTED = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "GOOGLE_API_KEY",
          "OPENAI_API_KEY", "OPENAI_BASE_URL"]

if not ENV.exists():
    sys.exit(f"missing: {ENV}")
vals = dotenv_values(ENV)
for k in WANTED:
    v = (vals.get(k) or "").strip()
    state = "set" if v else "MISSING"
    extra = ""
    if k == "LIVEKIT_URL" and v:
        extra = " (wss:// ok)" if v.startswith("wss://") else " (should start with wss://)"
    if v and (v.startswith("<") or "..." in v or " " in v or v[0] in "'\""):
        extra += " (looks like a placeholder or has quotes/spaces)"
    print(f"{k:20s} {state}{extra}")

missing = [k for k in WANTED[:3] if not (vals.get(k) or "").strip()]
if missing:
    sys.exit(f"cannot test LiveKit, missing {missing}")


async def main():
    from livekit import api, rtc
    token = (api.AccessToken(vals["LIVEKIT_API_KEY"], vals["LIVEKIT_API_SECRET"])
             .with_identity("connectivity-check")
             .with_grants(api.VideoGrants(room_join=True, room="connectivity-check"))
             .to_jwt())
    room = rtc.Room()
    try:
        await asyncio.wait_for(room.connect(vals["LIVEKIT_URL"], token), timeout=20)
        print("LiveKit: connected OK to room", room.name)
    except Exception as e:
        msg = str(e)
        for k in ("LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"):
            msg = msg.replace(vals[k], "***")
        print("LiveKit: connection FAILED:", type(e).__name__, msg[:200])
    finally:
        await room.disconnect()

asyncio.run(main())
