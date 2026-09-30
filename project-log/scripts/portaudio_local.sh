#!/usr/bin/env bash
# Try to get PortAudio working without sudo: download the .deb files and unpack them locally.
mkdir -p ~/theme5/localdeb && cd ~/theme5/localdeb
apt-get download libportaudio2 libasound2-plugins libjack-jackd2-0 2>&1 | tail -3
for d in *.deb; do dpkg -x "$d" root; done
find root -name "libportaudio.so*" -o -name "libasound_module_pcm_pulse.so" -o -name "libjack.so*" | head
ldconfig -p | grep -E "libasound.so|libpulse.so|libjack" | head -5
