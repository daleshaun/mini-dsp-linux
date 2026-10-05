# 2010 Mac mini Wi-Fi patch

Status: code and rollback tests pass; driver compilation and physical Wi-Fi behavior remain to be verified. A driver match is not proof that the radio associates reliably.

The build includes `broadcom-wl-dkms` with the LTS kernel's matching headers. The current upstream Omarchy hardware script explicitly installs this package for PCI IDs 14e4:4331 and 14e4:43a0; it does not include the older BCM4322 in that selector. The new tool checks the actual card against the compiled module's supported aliases, rather than assuming every mini has the same card.

The image uses NetworkManager, with a candidate default that disables power saving only on `wl` interfaces. A profile with an explicit power-saving value overrides that default. The patch does not weaken Wi-Fi encryption, change the regulatory country, disable Bluetooth, or force a frequency band. No Wi-Fi credentials are embedded in the image.

## On the new image

`mini-wifi status` reports the model, PCI ID, bound driver, kernel version and whether the matching `wl` module exists. The boot service stages the settings automatically only on Macmini4,1 with one supported Broadcom PCI Wi-Fi card. The `wl` package's normal driver aliases and conflict blacklist are included in the image so the driver can load without an internet download.

This image is specifically a 2010-mini build. The package's standard blacklist also exists independently of our guarded tool; this is not a general-purpose Broadcom driver selector for arbitrary machines.

## On an existing Omarchy installation

The standalone tool does not download packages. First install the matching kernel headers and `broadcom-wl-dkms` through a complete, consistent Arch update. If the kernel changed, boot the new kernel before running the patch. Do not install a driver built for another kernel.

From the extracted source folder:

```sh
python3 tools/mini-wifi status
python3 tools/mini-wifi plan
sudo python3 tools/mini-wifi apply
sudo mkinitcpio -P
```

Reboot when convenient. Applying the patch never unloads modules or restarts networking, so it does not deliberately sever the current connection.

To restore the configuration that existed before the custom patch:

```sh
sudo python3 tools/mini-wifi rollback
sudo mkinitcpio -P
```

Then reboot. Rollback disables automatic reapplication by this image's service. A later explicit `apply` re-enables it. It restores our configuration changes, not package installations or kernel upgrades. If you edited a patched file afterwards, the tool refuses to overwrite that edit.

## Hardware validation still required

1. Run `mini-wifi status` on the mini. Confirm Macmini4,1, the actual PCI ID, a kernel-matched module and `wl` after reboot.
2. Connect through NetworkManager. Verify reconnect after reboot, suspend/resume if you intend to use it, and both router bands supported by the card.
3. Inspect `journalctl -b -k` and `journalctl -b -u NetworkManager` for driver/association failures. These logs can include network identifiers; do not publish credentials.
4. Check the selected connection's `802-11-wireless.powersave` setting if the default appears ineffective. Value 0 inherits defaults, while 2 explicitly disables power saving.
5. Measure sustained LAN throughput and packet loss against another machine, then test the intended audio workload. Working Wi-Fi does not establish bounded latency for live DSP; wired Ethernet is the initial audio transport target.

## Evidence

- Upstream `omacom/omarchy` at `5c4da021469517449770579793b37ce26d0a0d48`, `install/hardware/fix-bcm43xx.sh`.
- Upstream ISO at `86c07785cb0f63be78edb1349843d5817b5c0e66`, `builder/build-iso.sh`: live ISO omits Broadcom wl; this edition adds DKMS plus headers.
- [Arch package](https://archlinux.org/packages/extra/x86_64/broadcom-wl-dkms/).
- [NetworkManager power-save values](https://networkmanager.dev/docs/api/latest/settings-802-11-wireless.html).
- [NetworkManager driver-specific defaults](https://networkmanager.dev/docs/api/latest/NetworkManager.conf.html).
