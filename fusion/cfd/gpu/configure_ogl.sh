#!/usr/bin/env bash
# OpenFOAM's environment initialization is not errexit-clean.
source /usr/lib/openfoam/openfoam2412/etc/bashrc
set -e -o pipefail
build_root=/home/repro/code/dell5560-cfd-gpu-20260908
test -f "$FOAM_LIBBIN/libOpenFOAM.so"
export FOAM_SRC="$build_root/foam-source/usr/lib/openfoam/openfoam2412/src"
export FOAM_USER_LIBBIN="$build_root/install/lib"
export HWLOC_COMPONENTS=linux,stop
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY
mpi_headers="$build_root/mpi-dev/usr/lib/x86_64-linux-gnu/openmpi/include"
cmake -S "$build_root/OGL" -B "$build_root/build" \
 -DCMAKE_BUILD_TYPE=Release \
 -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.4/bin/nvcc \
 -DCMAKE_CUDA_ARCHITECTURES=86 -DOGL_CUDA_ARCHITECTURES=86 \
 -DOGL_BUILD_CUDA=ON -DOGL_BUILD_OMP=ON -DOGL_BUILD_HIP=OFF \
 -DGINKGO_FORCE_GPU_AWARE_MPI=OFF \
 -DMPI_SKIP_COMPILER_WRAPPER=TRUE \
 -DMPI_CXX_HEADER_DIR="$mpi_headers" -DMPI_C_HEADER_DIR="$mpi_headers" \
 -DMPI_CXX_COMPILER_INCLUDE_DIRS="$mpi_headers;$mpi_headers/openmpi" \
 -DMPI_C_COMPILER_INCLUDE_DIRS="$mpi_headers;$mpi_headers/openmpi" \
 '-DMPI_CXX_LIB_NAMES=mpi_cxx;mpi' -DMPI_C_LIB_NAMES=mpi \
 -DMPI_mpi_LIBRARY=/usr/lib/x86_64-linux-gnu/libmpi.so.40 \
 -DMPI_mpi_cxx_LIBRARY=/usr/lib/x86_64-linux-gnu/libmpi_cxx.so.40 \
 -DCMAKE_INSTALL_PREFIX="$build_root/install" 2>&1 | tee "$build_root/configure.log"
