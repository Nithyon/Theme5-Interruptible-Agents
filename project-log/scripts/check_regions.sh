#!/usr/bin/env bash
for L in asia-south1 asia-southeast1 europe-west4 us-central1; do
  ~/theme5/fdb-env/bin/python /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/check_vertex.py hackathon-cinemahackathon "$L" 2>&1 | grep -E 'Vertex|3.8-live' | head -2
done
