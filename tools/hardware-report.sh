#!/usr/bin/env bash
# Run on the target mini. Read-only; does not probe FireWire devices or start audio.
set -u
run() { printf '\n--- %s ---\n' "$*"; if command -v "$1" >/dev/null 2>&1; then "$@" 2>&1 || true; else printf 'Unavailable\n'; fi; }
run uname -a
case "$(uname -s)" in
  Darwin)
    run sysctl hw.model hw.memsize machdep.cpu.brand_string machdep.cpu.features
    run system_profiler SPDisplaysDataType
    run diskutil list
    ;;
  Linux)
    run cat /sys/class/dmi/id/sys_vendor
    run cat /sys/class/dmi/id/product_name
    run cat /sys/class/dmi/id/board_name
    run lscpu
    run free -h
    run lspci -nnk
    run lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS
    run cat /proc/asound/cards
    run ip -brief link
    run rfkill list
    ;;
  *) printf 'Unsupported reporting platform\n' ;;
esac
