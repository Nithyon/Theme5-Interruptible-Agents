#!/usr/bin/env bash
# Fetch the two real-voice (CANDOR) subsets of Full-Duplex-Bench v1.0 from the authors' Drive
# (link in v1_v1.5/dataset/README.md). Rate-limited so a live benchmark run is not disturbed.
set -u
D=~/theme5/fdb_v1_data; mkdir -p "$D"; cd "$D"
get() { curl -sS -L --fail --limit-rate "${RATE:-2M}" -o "$2" "https://drive.usercontent.google.com/download?id=$1&export=download&confirm=t" && ls -la "$2"; }
get 1uls3atEz7bZ1IkVq3Rw0yQyLAjjVkklc candor_pause_handling.zip
get 1sb9mwOqDCK9BEpMb6fDVYOJU1vd5RFlb candor_turn_taking.zip
for z in candor_pause_handling.zip candor_turn_taking.zip; do file "$z"; unzip -q -o "$z" && echo "unzipped $z"; done
ls; du -sh .
