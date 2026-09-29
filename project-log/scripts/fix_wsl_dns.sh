#!/usr/bin/env bash
# Let WSL generate /etc/resolv.conf itself (with dnsTunneling=true in .wslconfig it
# forwards to Windows' DNS). Run as root: wsl -d Ubuntu -u root -- bash <this file>
set -e
sed -i 's/generateResolvConf = false/generateResolvConf = true/' /etc/wsl.conf
if [ -f /etc/resolv.conf ] && [ ! -L /etc/resolv.conf ]; then
  # the old file was locked with the immutable flag so WSL couldn't replace it
  chattr -i /etc/resolv.conf 2>/dev/null || true
  mv /etc/resolv.conf /etc/resolv.conf.bak
fi
echo "wsl.conf now:"; cat /etc/wsl.conf
echo "Old resolv.conf saved as /etc/resolv.conf.bak. Now run: wsl --shutdown"
