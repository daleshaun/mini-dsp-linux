#!/usr/bin/env bash
set -euo pipefail
echo 'MINI_DSP_DIAGNOSTICS_BEGIN'
uname -a
lscpu
echo 'Built Wi-Fi module:'
modinfo -F vermagic wl
test "$(modinfo -F vermagic wl | cut -d ' ' -f 1)" = "$(uname -r)"
mini-wifi status
NetworkManager --print-config
echo 'MINI_DSP_SMOKE_OK'
