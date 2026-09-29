#!/usr/bin/env bash
# Which realtime model ids the installed LiveKit plugins know about (task G2).
source ~/theme5/fdb-env/bin/activate
uv pip show livekit-agents livekit-plugins-google livekit-plugins-openai livekit-plugins-xai 2>/dev/null | grep -E '^(Name|Version)'
SP=$(python -c 'import site; print(site.getsitepackages()[0])')
for p in google openai xai; do
  echo "=== $p realtime model ids / defaults"
  grep -rhoE '"(gemini|gpt|grok)[-a-z0-9.]*(live|realtime|audio|voice|think|fast)[-a-z0-9.]*"' "$SP/livekit/plugins/$p" 2>/dev/null | sort -u | head -40
  grep -rhE 'model: .*= *"|DEFAULT_MODEL|model="' "$SP/livekit/plugins/$p/realtime" 2>/dev/null | sed 's/^ *//' | sort -u | head -8
done
