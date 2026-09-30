#!/usr/bin/env bash
cd ~/theme5/fdb_v1_data && ls -la && du -sh .
for t in */; do
  echo "== $t $(ls "$t" | wc -l) entries"; ls "$t" | head -4
  d="$t$(ls "$t" | head -1)"; ls "$d"
  for j in "$d"/*.json; do echo "-- $j"; head -c 700 "$j"; echo; done
done
