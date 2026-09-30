# source this: mic/speaker support for LiveKit console mode under WSLg without sudo
# (PortAudio + the ALSA->PulseAudio plugin unpacked locally by portaudio_local.sh).
L=$HOME/theme5/localdeb/root/usr/lib/x86_64-linux-gnu
export LD_LIBRARY_PATH="$L:${LD_LIBRARY_PATH:-}"
export ALSA_PLUGIN_DIR="$L/alsa-lib"
export PULSE_SERVER="${PULSE_SERVER:-unix:/mnt/wslg/PulseServer}"
[ -f ~/.asoundrc ] || printf 'pcm.!default { type pulse }\nctl.!default { type pulse }\n' > ~/.asoundrc
[ -e "$L/libportaudio.so" ] || ln -s libportaudio.so.2 "$L/libportaudio.so"
# sounddevice locates PortAudio with ctypes.util.find_library, which ignores LD_LIBRARY_PATH
# on some setups; a tiny startup hook points it at the local copy.
mkdir -p ~/theme5/localdeb/py
cat > ~/theme5/localdeb/py/sitecustomize.py <<PY
import ctypes.util as _u
_orig = _u.find_library
def _find(name):
    return "$L/libportaudio.so.2" if name == "portaudio" else _orig(name)
_u.find_library = _find
PY
export PYTHONPATH="$HOME/theme5/localdeb/py:${PYTHONPATH:-}"
