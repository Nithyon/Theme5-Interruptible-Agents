"""Deterministic mock tools for the extension demo: an in-car assistant that reroutes
navigation, checks traffic, and books EV charging, plus a permanently-down roadside-dispatch
line to exercise the handoff path. No network calls. Behaviour is controlled entirely by a
seed, so the same seed always produces the same sequence of delays/failures — useful for a
repeatable demo and for offline tests.
"""
from __future__ import annotations

import asyncio
import random
from typing import Dict

from recovery import ToolFailure


class MockBackend:
    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)
        self.bookings: Dict[str, dict] = {}       # keyed by "station_id|time_slot"
        self.reroutes: list = []
        self._charging_attempts: Dict[str, int] = {}

    # -- read-only, fast, reliable -----------------------------------------------------
    async def reroute_navigation(self, destination: str) -> dict:
        await asyncio.sleep(0.05)
        self.reroutes.append(destination)
        return {"status": "success", "destination": destination,
                "eta_min": self.rng.randint(5, 40)}

    # -- read-only, slow (3-8s in a real demo; tests pass a shorter delay range) --------
    async def check_traffic(self, route_id: str, delay_range=(3.0, 8.0)) -> dict:
        delay = self.rng.uniform(*delay_range)
        await asyncio.sleep(delay)
        return {"status": "success", "route_id": route_id,
                "congestion": self.rng.choice(["light", "moderate", "heavy"])}

    # -- read-only, fails intermittently (flaky upstream, not a permanent outage) -------
    async def find_charging_station(self, near: str, connector_type: str) -> dict:
        key = near + "|" + connector_type
        n = self._charging_attempts.get(key, 0)
        self._charging_attempts[key] = n + 1
        await asyncio.sleep(0.05)
        if n < 2:  # fails the first two attempts for a given (near, connector), then succeeds
            raise ToolFailure(f"charging-network lookup timed out for {near}")
        return {"status": "success", "station_id": f"CHG-{abs(hash(key)) % 1000:03d}",
                "near": near, "connector_type": connector_type,
                "distance_km": round(self.rng.uniform(0.5, 5.0), 1)}

    # -- state-changing, must be idempotent (never book the same slot twice) -----------
    async def book_charging_slot(self, station_id: str, time_slot: str) -> dict:
        key = station_id + "|" + time_slot
        await asyncio.sleep(0.05)
        if key in self.bookings:
            return self.bookings[key]  # already booked: same result, no new booking made
        booking = {"status": "success", "booking_id": f"BOOK-{len(self.bookings) + 1:04d}",
                   "station_id": station_id, "time_slot": time_slot}
        self.bookings[key] = booking
        return booking

    # -- state-changing, permanently down in this mock -> exercises the handoff path ----
    async def call_roadside_assistance(self, issue: str) -> dict:
        await asyncio.sleep(0.05)
        raise ToolFailure(f"dispatch line unreachable for: {issue}")
