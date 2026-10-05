#!/usr/bin/env bash
# Runs inside the freshly installed Linux target, not on the build host.
set -euo pipefail
[[ $(uname -s) == Linux && $EUID == 0 ]] || exit 1
assets=/usr/share/mini-dsp
install -Dm755 "$assets/mini-wifi" /usr/local/bin/mini-wifi
install -Dm755 "$assets/hardware-report.sh" /usr/local/bin/mini-dsp-hardware-report
install -Dm644 "$assets/70-mini-dsp.conf" /etc/pipewire/pipewire.conf.d/70-mini-dsp.conf
install -Dm644 "$assets/mini-dsp-wifi.service" /etc/systemd/system/mini-dsp-wifi.service
systemctl enable mini-dsp-wifi.service
# rtkit supplies realtime scheduling without giving every user unlimited rights.
# Explicit extra group privileges are limited to the selected installation user.
if [[ -n ${1:-} ]] && id "$1" >/dev/null 2>&1 && getent group realtime >/dev/null; then
    usermod -a -G realtime "$1"
fi
mkdir -p /usr/share/applications
cat > /usr/share/applications/mini-dsp-wifi.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Mini DSP Wi-Fi Report
Comment=Show hardware, loaded driver and patch eligibility
Exec=sh -c "mini-wifi status; printf '\nPress Enter to close'; read answer"
Terminal=true
Categories=System;Network;
EOF
