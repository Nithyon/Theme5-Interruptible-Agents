#!/usr/bin/env bash
source ~/theme5/fdb-env/bin/activate
python -c "import soundfile as sf; i=sf.info('$HOME/theme5/fdb_v1_data/candor_pause_handling/1/input.wav'); print(i.samplerate, i.channels, round(i.duration,1))"
O=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-30_smart_turn_fdbv1; mkdir -p "$O"
OMP_NUM_THREADS=4 nice -n 10 python /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/smart_turn_eval.py ~/theme5/fdb_v1_data "$O/eval_tail${TAIL_S:-0.2}_cap${CAP:-1}.json" 2>&1 | grep -v Warning | tee "$O/eval_tail${TAIL_S:-0.2}_cap${CAP:-1}.txt"
