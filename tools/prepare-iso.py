#!/usr/bin/env python3
"""Apply the local edition overlay to the pinned upstream ISO checkout."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ISO = ROOT / "upstream-iso"
PIN = "86c07785cb0f63be78edb1349843d5817b5c0e66"


def replace(path, old, new):
    text = path.read_text()
    if new in text:
        return
    if text.count(old) != 1:
        raise RuntimeError(f"Upstream layout changed: {path}: {old[:70]}")
    path.write_text(text.replace(old, new, 1))


def main():
    commit = subprocess.check_output(["git", "-C", str(ISO), "rev-parse", "HEAD"], text=True).strip()
    if commit != PIN:
        raise RuntimeError(f"Expected upstream {PIN}, got {commit}")
    config = ISO / "configs"
    live = config / "airootfs"
    assets = live / "usr/share/mini-dsp"
    assets.mkdir(parents=True, exist_ok=True)
    for source in ["tools/mini-wifi", "tools/setup-target.sh", "tools/hardware-report.sh",
                   "config/70-mini-dsp.conf", "config/mini-dsp-wifi.service", "config/audio.packages"]:
        shutil.copy2(ROOT / source, assets / Path(source).name)

    # Keep the official installer and desktop. Boot a stock LTS kernel on this
    # pre-T2 model rather than the upstream live image's T2-specific kernel.
    build = ISO / "builder/build-iso.sh"
    replace(build, 'pacman --noconfirm -Syu archiso git', 'pacman --noconfirm -Syu --needed archiso git')
    replace(build,
            '  rm -rf "$bootstrap_cache_dir" /tmp/offlinedb-bootstrap /tmp/omarchy-pkglists',
            '''  # Keep validated dependency archives on a retry; refresh the runtime itself.
  rm -rf /tmp/offlinedb-bootstrap /tmp/omarchy-pkglists
  if [[ -d $bootstrap_cache_dir ]]; then
    find "$bootstrap_cache_dir" -maxdepth 1 -type f -name "$OMARCHY_RUNTIME_PACKAGE-[0-9]*.pkg.tar.*" -delete
  fi''')
    replace(build, 'mkdir -p /tmp/offlinedb\ndownload_offline_packages()',
            '# This dedicated download-only database may retain a lock after an interrupted VM build.\n'
            'rm -f /tmp/offlinedb/db.lck\nmkdir -p /tmp/offlinedb\ndownload_offline_packages()')
    # The stable mirror currently lacks this T2-only package. The 2010 mini's
    # wl path does not use it; do not invent or substitute another firmware blob.
    replace(build,
            '  printf \'%s\\n\' "${all_packages[@]}" | sed \'s/^broadcom-wl$/broadcom-wl-dkms/\' | sort -u',
            '  printf \'%s\\n\' "${all_packages[@]}" | sed \'s/^broadcom-wl$/broadcom-wl-dkms/; /^apple-bcm-firmware$/d\' | sort -u')
    # Retain failed build state for diagnosis and retry inside the disposable VM.
    replace(ISO / "bin/omarchy-iso-make", '  --rm\n  --privileged',
            '  --name mini-dsp-iso-build\n  --privileged')
    replace(build, "arch_packages=(linux-t2 git", "arch_packages=(linux-lts linux-lts-headers broadcom-wl-dkms networkmanager wpa_supplicant python git")
    replace(build,
            'cp "${base_pkg_lists[1]}" "$build_cache_dir/airootfs/usr/share/omarchy-iso/omarchy-other.packages"',
            'cp "${base_pkg_lists[1]}" "$build_cache_dir/airootfs/usr/share/omarchy-iso/omarchy-other.packages"\n'
            'cat /configs/airootfs/usr/share/mini-dsp/audio.packages >> "$build_cache_dir/airootfs/usr/share/omarchy-iso/omarchy-base.packages"')
    replace(build, '    cat "$build_cache_dir/packages.x86_64"',
            '    cat "$build_cache_dir/packages.x86_64"\n    cat /configs/airootfs/usr/share/mini-dsp/audio.packages')
    # Check DKMS actually produced the live kernel module; a successful pacman
    # transaction alone is insufficient evidence that its DKMS hook succeeded.
    replace(build,
            '# Match host UID/GID on output.',
            '''# mini-dsp: reject images whose live Wi-Fi module was not built.
live_root="$build_cache_dir/work/x86_64/airootfs"
test -d "$live_root/usr/lib/modules"
for pkgbase in "$live_root"/usr/lib/modules/*/pkgbase; do
  [[ $(cat "$pkgbase") == linux-lts ]] || continue
  kver=$(basename "$(dirname "$pkgbase")")
  arch-chroot "$live_root" modinfo -k "$kver" wl >/out/mini-dsp-wl-module.txt
done
test -s /out/mini-dsp-wl-module.txt
arch-chroot "$live_root" pacman -Q >/out/mini-dsp-live-packages.txt
cp "$live_root/usr/share/omarchy-iso/omarchy-base.packages" /out/mini-dsp-target-packages.txt
sha256sum /out/*.iso >/out/SHA256SUMS

# Match host UID/GID on output.''')

    preset = live / "etc/mkinitcpio.d/linux-t2.preset"
    dest = preset.with_name("linux-lts.preset")
    if preset.exists():
        dest.write_text(preset.read_text().replace("linux-t2", "linux-lts"))
        preset.unlink()
    # This blacklist was specifically a workaround for linux-t2 on pre-T2 Macs.
    (live / "etc/modprobe.d/blacklist-applesmc.conf").unlink(missing_ok=True)
    for directory in ["grub", "syslinux", "efiboot"]:
        for p in (config / directory).rglob("*"):
            if p.is_file():
                p.write_text(p.read_text().replace("linux-t2", "linux-lts"))
    replace(config / "grub/grub.cfg", "timeout=0\ntimeout_style=hidden", "timeout=8\ntimeout_style=menu")
    grub = config / "grub/grub.cfg"
    if "mini-dsp-diagnostics" not in grub.read_text():
        grub.write_text(grub.read_text() + '''
menuentry "Mini DSP diagnostics (no installer)" --hotkey d --id mini-dsp-diagnostics {
    linux /%INSTALL_DIR%/boot/%ARCH%/vmlinuz-linux-lts archisobasedir=%INSTALL_DIR% archisosearchuuid=%ARCHISO_UUID% mini_dsp_diagnostics=1 console=tty0 console=ttyS0,115200
    initrd /%INSTALL_DIR%/boot/%ARCH%/initramfs-linux-lts.img
}
menuentry "Mini DSP basic graphics installer" --hotkey b --id mini-dsp-basic {
    linux /%INSTALL_DIR%/boot/%ARCH%/vmlinuz-linux-lts archisobasedir=%INSTALL_DIR% archisosearchuuid=%ARCHISO_UUID% nomodeset
    initrd /%INSTALL_DIR%/boot/%ARCH%/initramfs-linux-lts.img
}
''')
    replace(live / "root/.automated_script.sh", '[[ $(tty) == /dev/tty1 ]] || exit 0',
            '[[ $(tty) == /dev/tty1 ]] || exit 0\n'
            "grep -qw 'mini_dsp_diagnostics=1' /proc/cmdline && exit 0")
    replace(config / "profiledef.sh", 'iso_name="omarchy"', 'iso_name="mini-dsp-omarchy"')
    replace(config / "profiledef.sh", 'iso_publisher="Omarchy <https://omarchy.org>"',
            'iso_publisher="Mini DSP custom build (unofficial Omarchy derivative)"')
    replace(config / "profiledef.sh", 'iso_application="Omarchy Installer"',
            'iso_application="Mini DSP / Omarchy Installer"')
    # Less expensive compression when building under CPU emulation.
    replace(config / "profiledef.sh", "'-Xcompression-level' '19'", "'-Xcompression-level' '3'")
    configurator = live / "root/configurator"
    replace(configurator, '    echo "linux-omarchy"', '    echo "linux-lts"')
    context = live / "usr/share/omarchy-iso/orchestrator/context.py"
    replace(context, '    return "linux-omarchy"', '    return "linux-lts"')
    phases = live / "usr/share/omarchy-iso/orchestrator/phases_impl.py"
    replace(phases,
            '        _run_target_setup_command(ctx, cmd)\n    finally:',
            '''        _run_target_setup_command(ctx, cmd)
        # mini-dsp assets are copied after the upstream system setup finishes.
        shutil.copytree(Path("/usr/share/mini-dsp"), ctx.target / "usr/share/mini-dsp", dirs_exist_ok=True)
        _run_target_setup_command(ctx, ["/bin/bash", "/usr/share/mini-dsp/setup-target.sh", ctx.username or ""])
    finally:''')
    # Live boot already uses wl's packaged modaliases and blacklists. Enable NM
    # instead of releng's iwd/networkd competing managers, and expose diagnostics.
    usrbin = live / "usr/local/bin"
    shutil.copy2(ROOT / "tools/mini-wifi", usrbin / "mini-wifi")
    shutil.copy2(ROOT / "tools/live-diagnostics.sh", usrbin / "mini-dsp-diagnostics")
    service = live / "etc/systemd/system/mini-dsp-wifi.service"
    service.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "config/mini-dsp-wifi.service", service)
    wants = service.parent / "multi-user.target.wants"
    wants.mkdir(exist_ok=True)
    link = wants / "mini-dsp-wifi.service"
    if not link.is_symlink():
        link.symlink_to("../mini-dsp-wifi.service")
    shutil.copy2(ROOT / "config/mini-dsp-diagnostics.service", service.parent / "mini-dsp-diagnostics.service")
    link = wants / "mini-dsp-diagnostics.service"
    if not link.is_symlink():
        link.symlink_to("../mini-dsp-diagnostics.service")
    for executable in ("mini-wifi", "mini-dsp-diagnostics"):
        entry = f'  ["/usr/local/bin/{executable}"]="0:0:755"'
        profile = config / "profiledef.sh"
        lines = profile.read_text().splitlines(keepends=True)
        seen = False
        unique = []
        for line in lines:
            if line.rstrip("\n") == entry:
                if seen:
                    continue
                seen = True
            unique.append(line)
        profile.write_text("".join(unique))
        if entry not in (config / "profiledef.sh").read_text():
            replace(config / "profiledef.sh", 'file_permissions=(', 'file_permissions=(\n' + entry)
    replace(build, '# Bring in our archiso profile additions.',
            '''# mini-dsp: NetworkManager owns live networking.
find "$build_cache_dir/airootfs/etc/systemd/system" -type l \\( -name 'iwd.service' -o -name 'systemd-networkd.service' -o -name 'systemd-networkd.socket' -o -name 'systemd-networkd-wait-online.service' \\) -delete
mkdir -p "$build_cache_dir/airootfs/etc/systemd/system/multi-user.target.wants"
ln -sf /usr/lib/systemd/system/NetworkManager.service "$build_cache_dir/airootfs/etc/systemd/system/multi-user.target.wants/NetworkManager.service"

# Bring in our archiso profile additions.''')
    print("Prepared pinned Omarchy ISO overlay: LTS live kernel, Wi-Fi and audio packages.")


if __name__ == "__main__":
    main()
