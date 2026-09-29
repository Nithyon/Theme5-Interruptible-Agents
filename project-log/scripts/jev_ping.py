"""Check the Jev key works and how fast it answers. Prints no secrets."""
import asyncio, os, sys, time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path.home() / "theme5/Full-Duplex-Bench/v3/.env.local")
sys.path.insert(0, "/mnt/d/Theme5-Interruptible-Agents/fdb_agent")
print("TYPESAFE_API_KEY", "set" if os.getenv("TYPESAFE_API_KEY") else "MISSING")
import jev
jev.TIMEOUT_S = 5.0                      # generous for a first call
async def main():
    j = jev.make_judge()
    if j is None:
        sys.exit("Jev disabled (no key?)")
    for text in ["track order 4471 please", "book me a flight to Boston, uh"]:
        t0 = time.monotonic(); p = await j.turn_state(text)
        print(f"turn_state {text!r}: {p} in {int((time.monotonic()-t0)*1000)} ms")
    t0 = time.monotonic()
    p = await j.followup({"tool": "search_flights", "args": {"destination": "Boston"}},
                         {"tool": "search_flights", "args": {"destination": "New York"}}, "no sorry, New York")
    print(f"followup correction case: {p} in {int((time.monotonic()-t0)*1000)} ms")
    print("stats:", j.stats)
asyncio.run(main())
