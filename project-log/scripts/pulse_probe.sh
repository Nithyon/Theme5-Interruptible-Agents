#!/usr/bin/env bash
# What do we have for a virtual microphone (to feed recorded lines to a talk-mode agent)?
which pactl paplay parecord 2>&1 | head -3
export PULSE_SERVER=unix:/mnt/wslg/PulseServer
pactl info 2>/dev/null | grep -i 'server name\|default sink\|default source'
pactl list short sources 2>/dev/null; pactl list short sinks 2>/dev/null
ls /mnt/d/Theme5-Interruptible-Agents/devset/audio | grep -i '^s31' ; ls /mnt/d/Theme5-Interruptible-Agents/devset/*.py
