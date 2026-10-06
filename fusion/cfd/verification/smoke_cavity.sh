#!/usr/bin/env bash
# Tiny isolated official tutorial; this is not the laptop/mount CFD case.
source /usr/lib/openfoam/openfoam2412/etc/bashrc
set -euo pipefail
case_dir=/mnt/f/Code/dell-5560-wall-mount/fusion/cfd/verification/tutorial_cavity_v2412
if [ -e "$case_dir" ]; then
    printf 'Refusing to overwrite previous cavity verification: %s\n' "$case_dir" >&2
    exit 2
fi
mkdir "$case_dir"
cp -a "$FOAM_TUTORIALS/incompressible/icoFoam/cavity/cavity/." "$case_dir/"
cd "$case_dir"
cp system/controlDict controlDict.vendor_original
foamDictionary system/controlDict -entry endTime -set 0.05 > log.configure 2>&1
foamDictionary system/controlDict -entry writeInterval -set 10 >> log.configure 2>&1
printf 'Official cavity; modified only local endTime/writeInterval; 30 s per-command timeout.\n' > verification_scope.txt
timeout 30s blockMesh > log.blockMesh 2>&1
timeout 30s checkMesh -allGeometry -allTopology > log.checkMesh 2>&1
timeout 30s icoFoam > log.icoFoam 2>&1
tail -n 12 log.icoFoam
printf 'Tiny official cavity solver smoke test completed. Mount benchmark not solved.\n'
