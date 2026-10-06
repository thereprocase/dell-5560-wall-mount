#!/usr/bin/env bash
set -euo pipefail
audit=/mnt/f/Code/dell-5560-wall-mount/fusion/cfd/vendor/openfoam
/usr/bin/python3 "$audit/verify_packages.py" > "$audit/preinstall-verification.log"
sudo -n apt-get --no-download -y --no-install-recommends install \
    openfoam2412=2412.260127-1 \
    openfoam2412-tools=2412.260127-1 \
    openfoam2412-tutorials=2412.260127-1 2>&1 | tee "$audit/install.log"
