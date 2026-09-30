#!/usr/bin/env bash
cd ~/theme5/fdb_v1_data || exit 1
for z in *.zip; do python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall('.')" "$z" && echo "extracted $z"; done
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/fdbv1_look.sh
