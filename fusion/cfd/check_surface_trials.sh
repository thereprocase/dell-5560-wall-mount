#!/usr/bin/env bash
source /usr/lib/openfoam/openfoam2412/etc/bashrc
set -eo pipefail
cd /mnt/f/Code/dell-5560-wall-mount/fusion/cfd/geometry_traced_repaired
for digits in 9 8 7; do
surfaceCheck -checkSelfIntersection "fluid_boundary_round${digits}.stl" > "surface_round${digits}.log" 2>&1
echo "digits $digits"
grep -E 'closed|illegal|self-intersect|unconnected' "surface_round${digits}.log"
done
