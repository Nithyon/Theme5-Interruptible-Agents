set -e
cd ~/theme5/ollama
rm -rf bin lib
nice -n 19 tar -xf /mnt/d/ollama_tmp.tar
rm -f /mnt/d/ollama_tmp.tar
ls -la bin; ls lib/ollama | head -20
~/theme5/ollama/bin/ollama --version 2>&1 | tail -2
