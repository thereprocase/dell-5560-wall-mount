#!/usr/bin/env bash
source /usr/lib/openfoam/openfoam2412/etc/bashrc
set -euo pipefail
cd /mnt/f/Code/dell-5560-wall-mount/fusion/cfd/cases/OpenCFD_v2412/installed_pressure10_v1
phase=${1:-surface}
if [ "$phase" = surface ]; then
 surfaceCheck -checkSelfIntersection constant/triSurface/fluid_boundary.stl > log.surfaceCheck 2>&1
 python3 - <<'PY'
from pathlib import Path
s=Path('log.surfaceCheck').read_text()
assert 'Surface is closed' in s,s[-2000:]
assert 'Surface is not self-intersecting' in s,s[-2000:]
assert 'Surface is not closed' not in s
print(s[-3500:])
PY
elif [ "$phase" = mesh ]; then
 test ! -d constant/polyMesh
 blockMesh > log.blockMesh 2>&1
 decomposePar > log.decomposeMesh 2>&1
 mpirun -np 8 snappyHexMesh -parallel -overwrite > log.snappyHexMesh 2>&1
 reconstructParMesh -constant > log.reconstructMesh 2>&1
 checkMesh -constant -allGeometry -allTopology > log.checkMesh 2>&1
 tail -40 log.checkMesh
elif [ "$phase" = zones ]; then
 topoSet > log.topoSet 2>&1
 tail -50 log.topoSet
elif [ "$phase" = solve ]; then
 decomposePar -force > log.decomposeSolve 2>&1
 mpirun -np 8 simpleFoam -parallel > log.simpleFoam 2>&1
 reconstructPar -latestTime > log.reconstructSolution 2>&1
 tail -50 log.simpleFoam
else
 echo "Unknown phase" >&2;exit 1
fi
