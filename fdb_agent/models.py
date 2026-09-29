"""Realtime model construction shared by our agents.

Gemini Live via an API key, or via Vertex AI with Application Default Credentials when
GOOGLE_GENAI_USE_VERTEXAI=true (bills the Cloud project in GOOGLE_CLOUD_PROJECT).
"""
import os


def gemini_live(model: str):
    from livekit.plugins import google
    from livekit.plugins.google.realtime import realtime_api

    kw = dict(model=model, voice=os.getenv("GOOGLE_VOICE", "Puck"))
    if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("1", "true", "yes"):
        # The plugin's hard-coded list marks gemini-3.8-live as AI-Studio-only, but
        # Vertex serves it (checked with project-log/scripts/check_vertex.py), so drop
        # it from that list for this process.
        realtime_api.KNOWN_GEMINI_API_MODELS = realtime_api.KNOWN_GEMINI_API_MODELS - {model}
        kw.update(vertexai=True, project=os.getenv("GOOGLE_CLOUD_PROJECT"),
                  location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
    return google.realtime.RealtimeModel(**kw)
