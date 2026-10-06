#!/usr/bin/env bash
source /usr/lib/openfoam/openfoam2412/etc/bashrc
set -eo pipefail
cd /mnt/f/Code/dell-5560-wall-mount/fusion/cfd/geometry_traced_repaired
for digits in 10 9 8; do
surfaceCheck -checkSelfIntersection "fluid_stabilized_${digits}.stl" > "stabilized_${digits}.log" 2>&1
echo "exponent $digits"
grep -E 'closed|illegal|self-intersect|unconnected' "stabilized_${digits}.log"
done
