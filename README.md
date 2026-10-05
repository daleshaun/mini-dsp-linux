# Mac mini 2010 DSP Linux

Status: custom Omarchy ISO assembly started in an isolated Linux VM. Eight tests covering Wi-Fi safeguards, rollback and installer kernel selection pass. No completed ISO or physical hardware compatibility claim yet.

Requested base: Omarchy (Arch Linux). Target: 2010 Intel Mac mini; exact installed RAM, storage, GPU and interface to be confirmed. Keep x86-64 baseline compatibility; do not compile with AVX or x86-64-v3 requirements. Existing UAD Satellite work is outside this project and remains untouched.

## Proposed audio roles

- Local native Linux effects rack: Carla, native LV2/VST plug-ins, initially EQ, dynamics, delay and reverb.
- PipeWire/WirePlumber audio and MIDI routing, JACK application compatibility and a graphical patchbay.
- Recording, playback, format conversion and offline rendering.
- Wired network DSP offload: transport depends on the main DAW. AudioGridder's Linux server is experimental, requiring a separate interoperability test; do not promise macOS AU or Windows plug-ins run natively on Linux.
- Remote administration after user accounts and authentication are configured.

Build choice: retain the Omarchy desktop and include an Xfce session as a fallback for the old GPU. This is an unofficial custom Omarchy derivative, using a stock LTS kernel on the pre-T2 mini. The main DAW/interface and required network plug-in transport remain unspecified.

## Wi-Fi

The user reported unreliable Wi-Fi with original Omarchy. The image now includes kernel-matched Broadcom DKMS, NetworkManager, a guarded Macmini4,1 configuration patch, and rollback. See [WIFI-PATCH.md](WIFI-PATCH.md) for scope, commands, and required hardware tests.

## Build source

`tools/prepare-iso.py` applies a version-checked overlay to official Omarchy ISO source at commit `86c07785cb0f63be78edb1349843d5817b5c0e66`; its ArchISO submodule is `424e78130db2af6c1ceb55b442d7914b1109ff2b`.

On a fresh checkout, clone that upstream into `upstream-iso`, check out the pinned commit, and initialize its submodule. Run `bash tools/build-in-linux.sh` inside an isolated x86_64 Linux environment with Docker, Python, git and sudo. The upstream builder uses package repositories and downloads several gigabytes. The pinned recipe does not freeze the package mirrors; preserve output manifests and image hashes for each build.

Audio package selection is in `config/audio.packages`. PipeWire settings are candidate starting values, not measured performance. The ISO builder checks that the live kernel's `wl` module exists before it reports success.

The boot menu includes **Mini DSP diagnostics (no installer)**, which runs basic system/module checks and skips the installation wizard, and **Mini DSP basic graphics installer**, which adds `nomodeset` for troubleshooting the live installer. The normal installed desktop still uses kernel graphics drivers.

The configured upstream repository is missing `apple-bcm-firmware`, an optional T2-only package in Omarchy's hardware bundle. This 2010-specific build excludes that package from the offline mirror; the Broadcom `wl` package and matching LTS headers remain included. This image is not a T2-Mac edition.

## Target evidence

Run `bash tools/hardware-report.sh` on the mini under its current OS. The report is read-only, does not enumerate FireWire endpoints and does not start audio. Disk identifiers and network interface identifiers may appear in the report. Also record the audio interface model, main computer/DAW and required plug-ins.

## Acceptance criteria

1. Boot the candidate image in an x86-64 VM with a Core 2-era CPU model, then boot the physical mini from removable media before changing its internal disk.
2. Verify EFI boot, graphics, Ethernet, storage, temperature and fan behavior on hardware.
3. Enumerate the chosen interface only once its intended use is confirmed; validate channels, supported sample rates and clock source.
4. Start with the candidate 48 kHz / 512-frame configuration. This is a conservative starting value, not measured end-to-end latency or a performance guarantee.
5. Measure DSP load, xruns, round-trip latency and recovery over at least an hour using the intended effect chain. Increase or decrease buffers based on evidence.
6. Test DAW-to-server interoperability, disconnection and reconnection before enabling unattended operation. Check restart, remote administration and session restoration.
7. Produce an ISO checksum, package/version manifest, build instructions and measured limitations with the image.

## Build environment

Current development host is Apple Silicon macOS with QEMU. Build VM storage is `/Volumes/sample libs/MINI-DSP-BUILD/builder.qcow2`, a new 100 GiB sparse overlay of the cached Debian base image. It does not alter the base or any physical disk partition. SSH is forwarded only on localhost port 2226; generated credentials are in ignored `.builder/` and are excluded from source bundles. Guest source is `/home/builder/mini-dsp-linux`; guest build log is `/home/builder/mini-dsp-build.log`. The build runs in an x86_64 Arch container inside that VM.

The retained Docker container is named `mini-dsp-iso-build`. Do not start a second build while it is running. `tools/build-in-linux.sh` can restart an exited container for a retry. Attempt 1 stopped before image assembly because of the missing T2 firmware; its guest log is `/home/builder/mini-dsp-build-attempt1.log`. Attempt 2 resolved 1328 packages (4831.80 MiB download) including the audio additions. Build image digest: `archlinux/archlinux@sha256:11d01905726c79e96cb796a6e299683325433a3f63468c435fcf6e31c649b4b1`.

## References checked 2026-10-03

- https://omarchy.org/manual/mac-support/ — general Intel Mac support, not model-specific certification.
- https://support.apple.com/en-sa/112588 — Mid 2010 hardware specifications.
- https://archlinux.org/packages/extra/x86_64/carla/ — native plug-in host package.
- https://docs.pipewire.org/page_man_pipewire_conf_5.html — audio configuration fields.
- https://audiogridder.com/download/ — Linux release marked experimental.
