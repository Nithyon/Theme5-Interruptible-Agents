"""Baseline FDB-v3 agent: the benchmark's stock template (lk_agent_tool.py), unchanged,
with the realtime model chosen by GEMINI_LIVE_MODEL (default gemini-3.8-live).

Run from the FDB v3 directory:
    LK_PROVIDER=gemini3_8 python /mnt/d/Theme5-Interruptible-Agents/fdb_agent/baseline_agent.py start
"""
import os
import sys

sys.path.insert(0, os.getcwd())                                   # the FDB v3 directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))    # this folder
import lk_agent_tool as stock            # noqa: E402
from livekit import agents               # noqa: E402
from models import gemini_live           # noqa: E402

MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.8-live")
_stock_get_model = stock.get_realtime_model


def get_realtime_model():
    if stock.PROVIDER.lower() == "gemini3_8":
        return gemini_live(MODEL)
    return _stock_get_model()


stock.get_realtime_model = get_realtime_model

if __name__ == "__main__":
    agents.cli.run_app(stock.server)
