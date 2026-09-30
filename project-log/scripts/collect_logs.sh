#!/usr/bin/env bash
# Copy every run's per-recording outputs (our agent's result JSON; never the benchmark's
# answer files) into the repo's run folders, and zip the agent's recorded audio for Drive.
D=~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs
A=/mnt/d/Theme5-Interruptible-Agents/logs-audio; mkdir -p "$A"
declare -A MAP=( [gemini3_8]=2026-09-29_full_gemini3_8 [gate_gemini38_final]=2026-09-29_full_gate_gemini38_final [gate_gemini38]=2026-09-29_full_gate_gemini38 [gate_gemini38_c]=2026-09-29_full_gate_gemini38_c )
echo "file kinds present:"; ls "$D" | head -2; ls "$D/$(ls "$D" | head -1)" | sed 's/[0-9a-f]\{8,\}/X/g' | sort | uniq -c
for P in "${!MAP[@]}"; do
  out="$R/${MAP[$P]}/per_recording"; mkdir -p "$out"; n=0
  for f in "$D"/*/result_$P.json; do [ -f "$f" ] || continue; cp "$f" "$out/$(basename "$(dirname "$f")").json"; n=$((n+1)); done
  w=$(ls "$D"/*/output_$P.wav 2>/dev/null | wc -l)
  if [ "$w" -gt 0 ] && [ ! -f "$A/agent_audio_$P.zip" ]; then (cd "$D" && zip -q -r "$A/agent_audio_$P.zip" . -i "*/output_$P.wav"); fi
  echo "$P: $n result files -> ${MAP[$P]}/per_recording ($(du -sh "$out" | cut -f1)); $w audio files -> $(ls -sh "$A/agent_audio_$P.zip" 2>/dev/null | cut -d' ' -f1)"
done
# practice runs (our own scenarios): results + audio
V=/mnt/d/Theme5-Interruptible-Agents/devset/audio
for L in A A2 B C D; do
  out="$R/2026-09-29_dev_dev_gate_gemini38_$L/per_recording"; n=0
  for f in "$V"/*/result_dev_gate_gemini38_$L.json; do [ -f "$f" ] || continue; mkdir -p "$out"; cp "$f" "$out/$(basename "$(dirname "$f")").json"; n=$((n+1)); done
  echo "dev $L: $n result files"
done
for f in /tmp/agent_tool_calls.log; do ls -la $f 2>/dev/null; done
