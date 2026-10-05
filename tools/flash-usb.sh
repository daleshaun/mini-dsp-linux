#!/usr/bin/env bash
# Safely write an ISO to a USB / external drive on macOS.
# Refuses internal disks, shows the target's size and name, and requires an
# explicit typed confirmation before erasing anything.
#
#   ./tools/flash-usb.sh /path/to/mini-dsp-omarchy.iso
#
# WARNING: writing an image ERASES the entire target drive. Make sure the
# drive you pick is NOT the one holding your build VM, project, or samples.
set -euo pipefail

[[ $(uname -s) == Darwin ]] || { echo "This helper is for macOS (uses diskutil)." >&2; exit 1; }

iso="${1:-}"
[[ -n "$iso" && -f "$iso" ]] || { echo "Usage: $0 /path/to/image.iso" >&2; exit 1; }
iso_size=$(du -h "$iso" | cut -f1)

echo "Image: $iso ($iso_size)"
echo
echo "External physical disks:"
diskutil list external physical || true
echo
read -r -p "Enter the TARGET disk id (e.g. disk4, NOT disk4s1): " disk
[[ "$disk" =~ ^disk[0-9]+$ ]] || { echo "Expected a whole-disk id like 'disk4'." >&2; exit 1; }

info=$(diskutil info "/dev/$disk") || { echo "No such disk /dev/$disk." >&2; exit 1; }

# Hard refusal: never touch an internal disk.
if echo "$info" | grep -qiE 'Internal:[[:space:]]+Yes'; then
    echo "REFUSING: /dev/$disk is an INTERNAL disk. Aborting." >&2
    exit 1
fi
# Require it to be a whole physical disk, not a volume.
if ! echo "$info" | grep -qiE 'Whole:[[:space:]]+Yes'; then
    echo "REFUSING: /dev/$disk is not a whole disk. Pick the disk, not a partition." >&2
    exit 1
fi

size=$(echo "$info" | awk -F': *' '/Disk Size/ {print $2; exit}')
name=$(echo "$info" | awk -F': *' '/(Device \/ Media Name|Volume Name)/ {print $2; exit}')
echo
echo "Target : /dev/$disk"
echo "Name   : ${name:-<unknown>}"
echo "Size   : ${size:-<unknown>}"
echo
echo "This will ERASE the entire drive above and write the image to it."
read -r -p "Type exactly  ERASE $disk  to proceed: " confirm
[[ "$confirm" == "ERASE $disk" ]] || { echo "Not confirmed. Aborting (nothing written)." >&2; exit 1; }

echo "-> Unmounting /dev/$disk ..."
diskutil unmountDisk "/dev/$disk"

echo "-> Writing image (raw device, this takes several minutes)..."
# rdisk = raw device (much faster); bs=4m is macOS dd syntax.
sudo dd if="$iso" of="/dev/r$disk" bs=4m status=progress

echo "-> Flushing and ejecting..."
sync
diskutil eject "/dev/$disk"
echo "Done. Boot the mini holding Option, or via rEFInd."
