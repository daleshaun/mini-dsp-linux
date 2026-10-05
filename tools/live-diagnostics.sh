#!/usr/bin/env bash
# Live (no-installer) diagnostics. Runs every check to completion and prints a
# clear pass/fail at the end, rather than aborting mid-report on the first
# mismatch, so the journal always shows the full picture.
set -uo pipefail
echo 'MINI_DSP_DIAGNOSTICS_BEGIN'
uname -a
lscpu
cat /sys/class/dmi/id/product_name 2>/dev/null || true

running="$(uname -r)"
wl_magic="$(modinfo -F vermagic wl 2>/dev/null || true)"
echo "Built Wi-Fi module vermagic: ${wl_magic:-<none>}"
if [ -n "$wl_magic" ] && [ "${wl_magic%% *}" = "$running" ]; then
    wl_ok=1
    echo "wl module matches running kernel $running"
else
    wl_ok=0
    echo "WARNING: wl module ('${wl_magic%% *}') does not match running kernel ($running)"
fi

mini-wifi status || true
NetworkManager --print-config 2>/dev/null || true

if [ "$wl_ok" = 1 ]; then
    echo 'MINI_DSP_SMOKE_OK'
else
    echo 'MINI_DSP_SMOKE_FAIL: wl module missing or kernel mismatch'
    exit 1
fi
