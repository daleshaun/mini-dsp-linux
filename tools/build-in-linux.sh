#!/usr/bin/env bash
# Run from this project in an isolated x86_64 Linux builder with Docker.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || {
  echo 'This build requires an x86_64 Linux VM with Docker.' >&2; exit 1;
}
python3 tools/prepare-iso.py
python3 -m unittest discover -s tests -v
cd upstream-iso
# Preserve package caches and avoid an interactive graphical boot offer.
if sudo docker container inspect mini-dsp-iso-build >/dev/null 2>&1; then
  [[ $(sudo docker inspect -f '{{.State.Running}}' mini-dsp-iso-build) == false ]] || {
    echo 'The ISO build is already running.' >&2; exit 1;
  }
  sudo docker start -a mini-dsp-iso-build
  [[ $(sudo docker inspect -f '{{.State.ExitCode}}' mini-dsp-iso-build) == 0 ]]
else
  ./bin/omarchy-iso-make --keep-pkg-cache --no-boot-offer
fi
# Upstream renames the ISO after returning from the container.
cd release
sha256sum ./*.iso > SHA256SUMS
