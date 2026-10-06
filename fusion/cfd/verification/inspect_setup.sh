#!/usr/bin/env bash
# Read-only solver/dictionary/surface verification. No mesh or flow solve here.
source /usr/lib/openfoam/openfoam2412/etc/bashrc
set -euo pipefail
task_root=/mnt/f/Code/dell-5560-wall-mount/fusion/cfd
report_dir="$task_root/verification"
mkdir -p "$report_dir"
{
    date -u +%Y-%m-%dT%H:%M:%SZ
    printf 'WM_PROJECT_VERSION=%s\n' "$WM_PROJECT_VERSION"
    dpkg-query -W -f='${Package} ${Version}\n' openfoam2412 openfoam2412-tools openfoam2412-tutorials
    command -v foamDictionary surfaceCheck blockMesh snappyHexMesh checkMesh simpleFoam icoFoam
    simpleFoam -help
} > "$report_dir/environment.txt" 2>&1
for case_dir in "$task_root"/cases/OpenCFD_v2412/q*_coarse; do
    case_name=$(basename "$case_dir")
    report="$report_dir/dictionary_${case_name}.txt"
    : > "$report"
    for input in "$case_dir"/0/* "$case_dir"/constant/*Properties "$case_dir"/system/*; do
        printf '\nFILE %s\n' "$input" >> "$report"
        foamDictionary "$input" -keywords >> "$report" 2>&1
    done
    printf 'All dictionaries parsed: %s\n' "$case_name"
done
cd "$report_dir"
surfaceCheck -checkSelfIntersection "$task_root/cases/OpenCFD_v2412/q20_coarse/constant/triSurface/fluid_boundary.stl" > "$report_dir/surfaceCheck.txt" 2>&1
for item in constant/turbulenceProperties constant/transportProperties system/fvSchemes system/fvSolution 0.orig/U 0.orig/k 0.orig/omega 0.orig/nut; do
    path="$FOAM_TUTORIALS/incompressible/simpleFoam/motorBike/$item"
    if [ -f "$path" ]; then
        printf '\nFILE %s\n' "$path"
        cat "$path"
    fi
done > "$report_dir/installed_motorBike_reference.txt"
printf 'Surface and installed SST tutorial inspection recorded in %s\n' "$report_dir"
