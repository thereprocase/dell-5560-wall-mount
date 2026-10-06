# CFD runtime and reproduction

The study used Ubuntu 24.04 packages openfoam and libopenfoam version
1912.200626-2build3, extracted into a local runtime with their shared-library
dependencies. No custom solver code or numerical algorithm patch was used.
Package downloads were checked against Ubuntu's published SHA-256 entries.

On a compatible Linux environment, install OpenFOAM and load its normal shell
environment. cfd_study.py uses the local cfd-runtime/foam/usr tree when present;
otherwise it uses the inherited PATH and OpenFOAM environment. Run
python run_cfd_sweep.py, then python analyze_cfd.py and python render_cfd.py.

Every case runs blockMesh, checkMesh and simpleFoam -noFunctionObjects. The
noFunctionObjects flag avoids a SHA1 stream incompatibility in this older
binary's function-object setup on the host. The solver still writes all flow
fields normally. analyze_cfd.py integrates written boundary fluxes and takes
adjacent-cell pressure for the zero-gradient intake patch. VTK exports use
foamToVTK -latestTime -ascii. The report records convergence honestly.

Boundary-condition/model APIs may differ in newer OpenFOAM releases. Preserve
all dictionaries and report the solver version when repeating the study.
