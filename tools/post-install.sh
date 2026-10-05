#!/usr/bin/env bash
# Finish a STOCK Omarchy install into the Mac-mini DSP box, over Ethernet.
# Run this on the installed mini (as your normal user; it will sudo), with a
# working wired connection. Installs the Broadcom Wi-Fi driver for the running
# kernel, the audio stack, low-latency PipeWire, realtime access, and applies
# the guarded Wi-Fi patch.
set -euo pipefail

command -v pacman >/dev/null || { echo "Arch/Omarchy only." >&2; exit 1; }
[ "$EUID" -ne 0 ] || { echo "Run as your normal user (it will sudo as needed)." >&2; exit 1; }
HERE="$(cd "$(dirname "$0")/.." && pwd)"

# Headers must match the kernel actually running, or DKMS can't build wl.
case "$(uname -r)" in
    *-lts)      HDR=linux-lts-headers ;;
    *-zen)      HDR=linux-zen-headers ;;
    *-hardened) HDR=linux-hardened-headers ;;
    *)          HDR=linux-headers ;;
esac
echo "Running kernel $(uname -r) -> headers: $HDR"

echo "== 1/4  kernel headers + build tools (so the wl module can compile) =="
sudo pacman -S --needed --noconfirm base-devel "$HDR"

echo "== 2/4  Broadcom driver + networking + audio stack =="
sudo pacman -S --needed --noconfirm \
    broadcom-wl-dkms networkmanager wpa_supplicant wireless-regdb iw rfkill \
    pipewire pipewire-alsa pipewire-jack pipewire-pulse wireplumber rtkit \
    realtime-privileges alsa-utils qpwgraph carla lsp-plugins calf ardour \
    audacity ffmpeg sox flac

echo "== 3/4  apply the guarded Wi-Fi patch (no-op if not a supported mini) =="
python3 "$HERE/tools/mini-wifi" status || true
if sudo python3 "$HERE/tools/mini-wifi" apply; then
    sudo mkinitcpio -P
    sudo systemctl enable --now NetworkManager
else
    echo "Wi-Fi patch not applied (model/card/module not eligible); see 'mini-wifi status'."
fi

echo "== 4/4  low-latency audio + realtime access =="
install -Dm644 "$HERE/config/70-mini-dsp.conf" \
    "$HOME/.config/pipewire/pipewire.conf.d/70-mini-dsp.conf"
sudo usermod -aG realtime,audio "$USER"

echo
echo "Done. Reboot (or log out/in) so the realtime group and Wi-Fi take effect."
echo "After reboot:  mini-wifi status   and   nmtui   to join Wi-Fi."
