"""Run the benchmark's own scorer with a Gemini judge on Vertex AI instead of gpt-4o.

The FDB-v3 scorers call `OpenAI().chat.completions.create(model="gpt-4o", ...)` with the
benchmark's own judge prompts. This wrapper leaves that code untouched and swaps in a
client that sends the same prompts to Vertex's OpenAI-compatible endpoint with a Gemini
model, authenticated with Application Default Credentials (no API key).

Because the scorer silently falls back to exact match when a judge reply can't be parsed,
we count every call and every unusable reply and print them, so a "judged" score is
never secretly an exact-match score.

Run from the FDB v3 directory (see judge_score.sh):
    python judge_vertex.py evaluate_pass_rate --benchmark ... --results-dir ... --provider P --output X --use-llm
Env: JUDGE_MODEL (default google/gemini-2.5-pro), GOOGLE_CLOUD_PROJECT, JUDGE_LOCATION (default global).
"""
import importlib
import json
import os
import re
import sys
import time

import google.auth
import google.auth.transport.requests
from openai import OpenAI

MODEL = os.getenv("JUDGE_MODEL", "google/gemini-2.5-pro")
PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "hackathon-cinemahackathon")
LOCATION = os.getenv("JUDGE_LOCATION", "global")
HOST = "aiplatform.googleapis.com" if LOCATION == "global" else f"{LOCATION}-aiplatform.googleapis.com"
BASE_URL = f"https://{HOST}/v1/projects/{PROJECT}/locations/{LOCATION}/endpoints/openapi"

stats = {"calls": 0, "ok": 0, "unparseable": 0, "errors": 0, "retries": 0}


def _parses(text):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    try:
        json.loads(t)
        return True
    except Exception:
        return False


class _Completions:
    def __init__(self, judge):
        self._judge = judge

    def create(self, **kw):
        kw["model"] = MODEL
        # Room for Gemini's internal reasoning; the scorer's 200-token cap would truncate
        # the JSON answer and trigger its silent exact-match fallback.
        kw["max_tokens"] = max(kw.get("max_tokens") or 0, 4096)
        kw.setdefault("reasoning_effort", "low")
        stats["calls"] += 1
        for attempt in range(5):
            try:
                resp = self._judge.client().chat.completions.create(**kw)
                if _parses(resp.choices[0].message.content):
                    stats["ok"] += 1
                else:
                    stats["unparseable"] += 1
                return resp
            except Exception as e:
                if attempt < 4 and ("429" in str(e) or "503" in str(e) or "RESOURCE_EXHAUSTED" in str(e)):
                    stats["retries"] += 1
                    time.sleep(2 ** attempt)
                    continue
                stats["errors"] += 1
                raise


class VertexJudge:
    """Minimal stand-in for openai.OpenAI(): only .chat.completions.create is used."""

    def __init__(self):
        self._creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        self._client = None
        self._expiry = 0
        self.chat = type("Chat", (), {})()
        self.chat.completions = _Completions(self)

    def client(self):
        if self._client is None or time.time() > self._expiry:
            self._creds.refresh(google.auth.transport.requests.Request())
            self._client = OpenAI(base_url=BASE_URL, api_key=self._creds.token)
            self._expiry = time.time() + 45 * 60      # access tokens last ~60 min
        return self._client


def main():
    target = sys.argv[1]                                # evaluate_pass_rate | evaluate_tool_calls
    sys.argv = [target + ".py"] + sys.argv[2:]
    sys.path.insert(0, os.getcwd())
    judge = VertexJudge()
    for name in ("evaluate_tool_calls", "evaluate_pass_rate"):
        try:
            mod = importlib.import_module(name)
            mod._openai_client = judge
        except Exception:
            pass
    try:
        importlib.import_module(target).main()
    finally:
        print(f"JUDGE {MODEL}: " + json.dumps(stats), file=sys.stderr)


if __name__ == "__main__":
    main()
