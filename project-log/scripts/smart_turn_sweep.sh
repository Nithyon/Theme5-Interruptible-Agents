#!/usr/bin/env bash
# Sensitivity of the offline check to how much silence the model hears (threshold stays 0.5).
for cfg in "0.0 1" "0.6 0" "1.0 0"; do set -- $cfg; echo "## tail=$1 cap=$2"; TAIL_S=$1 CAP=$2 bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/smart_turn_eval.sh | tail -3; done
python3 - <<'PY'
import json,os,soundfile as sf,numpy as np
r=os.path.expanduser('~/theme5/fdb_v1_data/candor_turn_taking')
for c in ['1','10','50']:
    a,sr=sf.read(f'{r}/{c}/input.wav'); t0,t1=json.load(open(f'{r}/{c}/turn_taking.json'))[0]['timestamp']
    rms=lambda x: round(float(np.sqrt((x**2).mean())),4) if len(x) else None
    print(c,'dur',round(len(a)/sr,1),'turn',round(t0,2),round(t1,2),'rms before',rms(a[int((t0-1)*sr):int(t0*sr)]),'gap',rms(a[int(t0*sr):int(t1*sr)]),'after',rms(a[int(t1*sr):int((t1+1)*sr)]))
PY
