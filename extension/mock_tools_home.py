"""Deterministic MOCK tools for the second scenario: a Bixby-style smart-home / device
assistant (SmartThings-like devices). These are mocks only -- no real SmartThings or Bixby
API is called, no network. Same conventions as mock_tools.MockBackend: async methods, behaviour
driven by a seed (EXT_SEED), deliberate slowness/flakiness so the recovery paths in
recovery.py get exercised.
"""
from __future__ import annotations

import asyncio
import os
import random
from typing import Dict

from recovery import ToolFailure


class HomeBackend:
    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)
        self.ac: Dict[str, float] = {}             # room -> target celsius
        self.lights: Dict[str, dict] = {}          # room -> {"state", "brightness"}
        self.washer_jobs: Dict[str, dict] = {}     # keyed by "cycle|delay_minutes"
        self._find_phone_attempts = 0
        self.lights_fail_first = os.getenv("EXT_LIGHTS_FAIL_FIRST", "0") == "1"
        self._lights_attempts: Dict[str, int] = {}

    # -- fast, idempotent (setting the same value twice is harmless) -------------------
    async def set_ac_temperature(self, room: str, celsius: float) -> dict:
        await asyncio.sleep(0.05)
        self.ac[room.strip().lower()] = celsius
        return {"status": "success", "room": room, "celsius": celsius}

    # -- fast ----------------------------------------------------------------------------
    async def set_lights(self, room: str, state: str, brightness: int = 100) -> dict:
        await asyncio.sleep(0.05)
        if self.lights_fail_first:  # EXT_LIGHTS_FAIL_FIRST=1: first attempt of each request fails
            key = f"{room.strip().lower()}|{state}|{brightness}"
            self._lights_attempts[key] = self._lights_attempts.get(key, 0) + 1
            if self._lights_attempts[key] == 1:
                raise ToolFailure("light hub did not acknowledge the command")
        self.lights[room.strip().lower()] = {"state": state, "brightness": brightness}
        return {"status": "success", "room": room, "state": state, "brightness": brightness}

    # -- state-changing, must never double-start the same job ---------------------------
    async def start_washer(self, cycle: str, delay_minutes: int = 0) -> dict:
        key = cycle.strip().lower() + "|" + str(delay_minutes)
        await asyncio.sleep(0.05)
        if key in self.washer_jobs and not self.washer_jobs[key].get("cancelled"):
            return self.washer_jobs[key]  # already running: same job, no second start
        job = {"status": "success", "job_id": f"WASH-{len(self.washer_jobs) + 1:04d}",
               "cycle": cycle, "delay_minutes": delay_minutes}
        self.washer_jobs[key] = job
        return job

    # -- state-changing, idempotent -> compensates a start_washer on rollback -----------
    async def cancel_washer(self, job_id: str) -> dict:
        await asyncio.sleep(0.05)
        for job in self.washer_jobs.values():
            if job["job_id"] == job_id:
                if job.get("cancelled"):
                    return {"status": "success", "job_id": job_id, "already_cancelled": True}
                job["cancelled"] = True
                return {"status": "success", "job_id": job_id, "cancelled": True}
        raise ToolFailure(f"no washer job found for {job_id}")

    # -- read-only, slow (3-6s in the demo; tests pass a shorter range) ------------------
    async def check_energy_usage(self, period: str = "today", delay_range=(3.0, 6.0)) -> dict:
        await asyncio.sleep(self.rng.uniform(*delay_range))
        return {"status": "success", "period": period,
                "kwh": round(self.rng.uniform(2.0, 15.0), 1)}

    # -- read-only, flaky: fails the first two attempts, then succeeds -------------------
    async def find_phone(self) -> dict:
        self._find_phone_attempts += 1
        await asyncio.sleep(0.05)
        if self._find_phone_attempts <= 2:
            raise ToolFailure("phone did not answer the ring request")
        return {"status": "success", "location": "living room sofa", "ringing": True}

    # -- permanently down in this mock -> exercises the human-handoff path ---------------
    async def call_service_center(self, issue: str) -> dict:
        await asyncio.sleep(0.05)
        raise ToolFailure(f"service centre line unreachable for: {issue}")
