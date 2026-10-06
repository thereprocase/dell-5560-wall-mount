"""Prepare an OpenCFD v2412 case without invoking any mesher or solver.

Python standard library only. Input patches are STL in metres, jointly forming
one consistently oriented closed fluid boundary. Existing cases are preserved.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import textwrap

PATCHES = (
    "fan_left", "fan_right", "outlet", "laptop_shell", "wall_plane",
    "assumed_side_seals", "printed_or_model_walls",
)
WALLS = PATCHES[3:]
CFM_TO_M3_S = 0.028316846592 / 60


def foam_header(name, cls="dictionary", location=None):
    where = f'    location "{location}";\n' if location else ""
    return ("/* Generated for OpenCFD OpenFOAM v2412; setup only. */\n"
            "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
            f"    class {cls};\n{where}    object {name};\n}}\n\n")


def fmt(value):
    return f"{value:.12g}"


def vec(values):
    return "(" + " ".join(fmt(v) for v in values) + ")"


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def read_triangles(path):
    """Read binary or ASCII STL; calculate normals from vertex winding."""
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0] if len(data) >= 84 else 0
    if len(data) >= 84 and len(data) == 84 + count * 50:
        triangles = []
        for index in range(count):
            values = struct.unpack_from("<12fH", data, 84 + index * 50)
            triangles.append(tuple(tuple(values[j:j+3]) for j in (3, 6, 9)))
    else:
        vertices = []
        for line in data.decode("ascii").splitlines():
            words = line.split()
            if words and words[0] == "vertex":
                if len(words) != 4:
                    raise ValueError(f"Malformed STL vertex: {path}")
                vertices.append(tuple(float(v) for v in words[1:]))
        if len(vertices) % 3:
            raise ValueError(f"Incomplete triangle: {path}")
        triangles = [tuple(vertices[i:i+3]) for i in range(0, len(vertices), 3)]
    if not triangles:
        raise ValueError(f"Empty required patch: {path}")
    for tri in triangles:
        if not all(math.isfinite(x) for point in tri for x in point):
            raise ValueError(f"Non-finite STL coordinate: {path}")
        if math.sqrt(dot(cross(sub(tri[1], tri[0]), sub(tri[2], tri[0])),
                         cross(sub(tri[1], tri[0]), sub(tri[2], tri[0])))) <= 1e-18:
            raise ValueError(f"Degenerate STL triangle: {path}")
    return triangles


def inspect_geometry(directory, config):
    patches, evidence, edges, directions = {}, {}, Counter(), Counter()
    lower, upper = [math.inf]*3, [-math.inf]*3
    volume = 0.0
    for patch in PATCHES:
        matches = [p for p in directory.iterdir() if p.is_file()
                   and p.stem == patch and p.suffix.lower() == ".stl"]
        if len(matches) != 1:
            raise ValueError(f"Expected one {patch}.stl in {directory}; found {len(matches)}")
        path = matches[0]
        triangles = read_triangles(path)
        patches[patch] = triangles
        area = 0.0
        for tri in triangles:
            n = cross(sub(tri[1], tri[0]), sub(tri[2], tri[0]))
            area += math.sqrt(dot(n, n)) / 2
            volume += dot(tri[0], cross(tri[1], tri[2])) / 6
            for point in tri:
                for axis, coordinate in enumerate(point):
                    lower[axis] = min(lower[axis], coordinate)
                    upper[axis] = max(upper[axis], coordinate)
            # Nanometre quantisation permits independent ASCII serialization.
            points = [tuple(round(x, 9) for x in point) for point in tri]
            for a, b in zip(points, points[1:] + points[:1]):
                edge = tuple(sorted((a, b)))
                edges[edge] += 1
                directions[edge] += 1 if a < b else -1
        evidence[patch] = {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                           "triangle_count": len(triangles), "area_m2": area}
    bad = sum(v != 2 for v in edges.values())
    reversed_edges = sum(v != 0 for v in directions.values())
    if bad or reversed_edges:
        raise ValueError(f"Fluid boundary not consistently closed: {bad} non-two-use edges, "
                         f"{reversed_edges} winding mismatches at 1e-9 m rounding")
    if volume <= 0:
        raise ValueError("Fluid boundary signed volume is not positive; check outward winding")
    domain = config["block_mesh_domain_m"]
    for axis in range(3):
        if not domain["min"][axis] < lower[axis] < upper[axis] < domain["max"][axis]:
            raise ValueError("Geometry not strictly inside metre-scale background domain")
    for axis, coordinate in enumerate(config["location_in_mesh_m"]):
        if not lower[axis] < coordinate < upper[axis]:
            raise ValueError("locationInMesh is outside the fluid bounding box")
    return patches, {"patches": evidence, "bounds_m": [lower, upper],
                     "signed_volume_m3": volume, "closed_edge_check": "passed",
                     "location_in_mesh_status": "inside bounding box; exact interior selected by geometry prep, mesher unverified"}


def combined_stl(patches):
    lines = []
    for name, triangles in patches.items():
        lines.append(f"solid {name}")
        for a, b, c in triangles:
            normal = cross(sub(b, a), sub(c, a))
            length = math.sqrt(dot(normal, normal))
            lines += ["  facet normal " + " ".join(fmt(x/length) for x in normal), "    outer loop"]
            lines += ["      vertex " + " ".join(fmt(x) for x in point) for point in (a, b, c)]
            lines += ["    endloop", "  endfacet"]
        lines.append(f"endsolid {name}")
    return "\n".join(lines) + "\n"


def field(name, dimensions, internal, patch_bodies):
    cls = "volVectorField" if name == "U" else "volScalarField"
    body = foam_header(name, cls, "0") + f"dimensions [{dimensions}];\ninternalField uniform {internal};\nboundaryField\n{{\n"
    for patch, values in patch_bodies.items():
        body += f"    {patch}\n    {{\n" + textwrap.indent(values, "        ") + "\n    }\n"
    return body + "}\n"


def field_files(q, config, geometry):
    turbulence = config["turbulence"]
    speeds = [q/geometry["patches"][p]["area_m2"] for p in PATCHES[:2]]
    k_values = [1.5*(turbulence["intensity"]*speed)**2 for speed in speeds]
    omega_values = [math.sqrt(k)/(0.09**0.25*turbulence["length_scale_m"]) for k in k_values]
    k0, omega0 = max(k_values), max(omega_values)
    u, p, k, omega, nut = {}, {}, {}, {}, {}
    for index, patch in enumerate(PATCHES[:2]):
        u[patch] = f"type flowRateInletVelocity;\nvolumetricFlowRate constant {fmt(q)};\nextrapolateProfile no;\nvalue uniform (0 0 0);"
        p[patch] = "type zeroGradient;"
        k[patch] = f"type fixedValue;\nvalue uniform {fmt(k_values[index])};"
        omega[patch] = f"type fixedValue;\nvalue uniform {fmt(omega_values[index])};"
        nut[patch] = "type calculated;\nvalue uniform 0;"
    u["outlet"] = "type pressureInletOutletVelocity;\nvalue uniform (0 0 0);"
    p["outlet"] = "type fixedValue;\nvalue uniform 0;"
    k["outlet"] = f"type inletOutlet;\ninletValue uniform {fmt(k0)};\nvalue uniform {fmt(k0)};"
    omega["outlet"] = f"type inletOutlet;\ninletValue uniform {fmt(omega0)};\nvalue uniform {fmt(omega0)};"
    nut["outlet"] = "type calculated;\nvalue uniform 0;"
    for patch in (*WALLS, "backgroundBox"):
        u[patch] = "type noSlip;"
        p[patch] = "type zeroGradient;"
        k[patch] = f"type kqRWallFunction;\nvalue uniform {fmt(k0)};"
        omega[patch] = f"type omegaWallFunction;\nvalue uniform {fmt(omega0)};"
        nut[patch] = "type nutkWallFunction;\nvalue uniform 0;"
    return {
        "0/U": field("U", "0 1 -1 0 0 0 0", "(0 0 0)", u),
        "0/p": field("p", "0 2 -2 0 0 0 0", "0", p),
        "0/k": field("k", "0 2 -2 0 0 0 0", fmt(k0), k),
        "0/omega": field("omega", "0 0 -1 0 0 0 0", fmt(omega0), omega),
        "0/nut": field("nut", "0 2 -1 0 0 0 0", "0", nut),
    }, {"per_fan_bulk_speed_m_s": speeds, "per_fan_k_m2_s2": k_values, "per_fan_omega_s_1": omega_values}


def block_mesh(config, level):
    a, b = config["block_mesh_domain_m"]["min"], config["block_mesh_domain_m"]["max"]
    vertices = [(a[0],a[1],a[2]), (b[0],a[1],a[2]), (b[0],b[1],a[2]), (a[0],b[1],a[2]),
                (a[0],a[1],b[2]), (b[0],a[1],b[2]), (b[0],b[1],b[2]), (a[0],b[1],b[2])]
    cells = [math.ceil((hi-lo)/level["base_cell_m"]) for lo, hi in zip(a, b)]
    return foam_header("blockMeshDict") + f"""scale 1;
vertices
(
{chr(10).join('    ' + vec(v) for v in vertices)}
);
blocks (hex (0 1 2 3 4 5 6 7) {vec(cells)} simpleGrading (1 1 1));
edges ();
boundary
(
    backgroundBox
    {{
        type wall;
        faces ((0 4 7 3) (1 2 6 5) (0 1 5 4) (3 7 6 2) (0 3 2 1) (4 5 6 7));
    }}
);
mergePatchPairs ();
"""


def snappy(config, level):
    mapping = "\n".join(f"            {p} {{ name {p}; }}" for p in PATCHES)
    region_types = "\n".join(f"                {p} {{ level ({level['surface_level']} {level['surface_level']}); patchInfo {{ type {'patch' if p in PATCHES[:3] else 'wall'}; }} }}" for p in PATCHES)
    layers = "\n".join(f"        {p} {{ nSurfaceLayers {level['wall_layers']}; }}" for p in WALLS)
    box = config["outlet_refinement_box_m"]
    return foam_header("snappyHexMeshDict") + f"""castellatedMesh true;
snap true;
addLayers true;
geometry
{{
    fluid_boundary.stl
    {{
        type triSurfaceMesh;
        name fluid;
        regions
        {{
{mapping}
        }}
    }}
    outletRefinement
    {{
        type searchableBox;
        min {vec(box['min'])};
        max {vec(box['max'])};
    }}
}}
castellatedMeshControls
{{
    maxLocalCells {level['max_global_cells']};
    maxGlobalCells {level['max_global_cells']};
    minRefinementCells 0;
    maxLoadUnbalance 0.1;
    nCellsBetweenLevels 3;
    features ();
    refinementSurfaces
    {{
        fluid
        {{
            level ({level['surface_level']} {level['surface_level']});
            patchInfo {{ type wall; }}
            regions
            {{
{region_types}
            }}
        }}
    }}
    resolveFeatureAngle 30;
    refinementRegions
    {{
        outletRefinement {{ mode inside; levels ((1e15 {level['outlet_level']})); }}
    }}
    locationInMesh {vec(config['location_in_mesh_m'])};
    allowFreeStandingZoneFaces true;
}}
snapControls
{{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 30;
    nRelaxIter 5;
    nFeatureSnapIter 10;
    implicitFeatureSnap true;
    explicitFeatureSnap false;
    multiRegionFeatureSnap false;
}}
addLayersControls
{{
    relativeSizes true;
    layers
    {{
{layers}
    }}
    expansionRatio 1.2;
    finalLayerThickness 0.3;
    minThickness 0.1;
    nGrow 0;
    featureAngle 60;
    nRelaxIter 5;
    nSmoothSurfaceNormals 1;
    nSmoothNormals 3;
    nSmoothThickness 10;
    maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3;
    minMedialAxisAngle 90;
    nBufferCellsNoExtrude 0;
    nLayerIter 50;
}}
meshQualityControls
{{
    maxNonOrtho 65;
    maxBoundarySkewness 20;
    maxInternalSkewness 4;
    maxConcave 80;
    minVol 1e-18;
    minTetQuality 1e-15;
    minArea -1;
    minTwist 0.02;
    minDeterminant 0.001;
    minFaceWeight 0.05;
    minVolRatio 0.01;
    minTriangleTwist -1;
    nSmoothScale 4;
    errorReduction 0.75;
}}
writeFlags (scalarLevels layerSets layerFields);
mergeTolerance 1e-6;
"""


def control(config):
    monitors = []
    for patch in PATCHES[:3]:
        for field_name, operation in (("phi", "sum"), ("p", "areaAverage")):
            monitors.append(f"""    {patch}_{field_name}
    {{
        type surfaceFieldValue;
        libs (fieldFunctionObjects);
        regionType patch;
        name {patch};
        operation {operation};
        fields ({field_name});
        writeFields false;
        log true;
        writeControl timeStep;
        writeInterval 10;
    }}""")
    return foam_header("controlDict") + f"""application simpleFoam;
startFrom startTime;
startTime 0;
stopAt endTime;
endTime {config['run_controls']['maximum_iterations']};
deltaT 1;
writeControl timeStep;
writeInterval {config['run_controls']['write_interval']};
purgeWrite 0;
writeFormat ascii;
writePrecision 10;
writeCompression off;
timeFormat general;
timePrecision 8;
runTimeModifiable true;
functions
{{
{chr(10).join(monitors)}
    wallResolution
    {{
        type yPlus;
        libs (fieldFunctionObjects);
        writeControl writeTime;
    }}
}}
"""


FV_SCHEMES = """ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; grad(U) cellLimited Gauss linear 1; }
divSchemes
{
    default none;
    div(phi,U) bounded Gauss linearUpwind grad(U);
    div(phi,k) bounded Gauss upwind;
    div(phi,omega) bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear limited 0.5; }
interpolationSchemes { default linear; }
snGradSchemes { default limited 0.5; }
wallDist { method meshWave; }
fluxRequired { default no; p; }
"""

FV_SOLUTION = """solvers
{
    p
    {
        solver GAMG;
        tolerance 1e-8;
        relTol 0.05;
        smoother GaussSeidel;
        cacheAgglomeration true;
        agglomerator faceAreaPair;
        nCellsInCoarsestLevel 20;
        mergeLevels 1;
    }
    "(U|k|omega)"
    {
        solver smoothSolver;
        smoother symGaussSeidel;
        tolerance 1e-8;
        relTol 0.1;
    }
}
SIMPLE
{
    nNonOrthogonalCorrectors 2;
    consistent yes;
    residualControl { p 1e-5; U 1e-5; k 1e-5; omega 1e-5; }
}
relaxationFactors
{
    fields { p 0.3; }
    equations { U 0.7; k 0.7; omega 0.7; }
}
"""

# Written into each case; runs only when explicitly invoked by a person.
ALLRUN = r'''#!/bin/sh
set -eu
cd "$(dirname "$0")"
case "${WM_PROJECT_VERSION:-}" in
    v2412|2412) ;;
    *) echo "Source OpenCFD OpenFOAM v2412 before running this case." >&2; exit 2 ;;
esac
[ "${WM_PROJECT:-}" = OpenFOAM ] || { echo "Wrong OpenFOAM environment" >&2; exit 2; }
for command in python3 blockMesh surfaceCheck snappyHexMesh checkMesh simpleFoam; do
    command -v "$command" >/dev/null 2>&1 || { echo "Missing $command" >&2; exit 2; }
done
# Verify the loaded executable agrees with the environment, without solving.
simpleFoam -help > version_check.txt 2>&1
grep -Eq 'OpenFOAM-v2412|OpenFOAM-2412' version_check.txt || {
    echo "simpleFoam executable is not identified as OpenCFD v2412" >&2; exit 2;
}
if [ -e constant/polyMesh ] || [ -e log.blockMesh ] || [ -e log.simpleFoam ]; then
    echo "This case has mesh/run evidence already; generate a fresh case to preserve it." >&2
    exit 2
fi
echo "Running explicitly requested sealed fixed-flow benchmark; no thermal or fan-curve solve."
surfaceCheck -checkSelfIntersection constant/triSurface/fluid_boundary.stl > log.surfaceCheck 2>&1
grep -q 'Surface is closed' log.surfaceCheck || { echo "Surface closure check failed" >&2; exit 3; }
if grep -q 'Surface is self-intersecting' log.surfaceCheck; then
    echo "Surface self-intersection reported; repair geometry before meshing." >&2
    exit 3
fi
blockMesh > log.blockMesh 2>&1
snappyHexMesh -overwrite > log.snappyHexMesh 2>&1
checkMesh -allGeometry -allTopology > log.checkMesh 2>&1
grep -q 'Mesh OK' log.checkMesh || { echo "Mesh checks did not pass; inspect log.checkMesh" >&2; exit 3; }
python3 verify_mesh.py
simpleFoam > log.simpleFoam 2>&1
echo "Solver returned. Inspect convergence, flux balance, yPlus and mesh sensitivity before using results."
'''

VERIFY_MESH = r'''"""Refuse wrong/missing/disconnected fluid boundaries before solving."""
from pathlib import Path
import re
expected = {"fan_left", "fan_right", "outlet", "laptop_shell", "wall_plane", "assumed_side_seals", "printed_or_model_walls"}
text = Path("constant/polyMesh/boundary").read_text()
text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
found = {}
for name, body in re.findall(r"([A-Za-z_][A-Za-z_0-9]*)\s*\{([^{}]*)\}", text):
    count = re.search(r"\bnFaces\s+(\d+)\s*;", body)
    kind = re.search(r"\btype\s+(\w+)\s*;", body)
    if count:
        found[name] = (int(count.group(1)), kind.group(1) if kind else "")
for name in expected:
    if name not in found or found[name][0] <= 0:
        raise SystemExit("Missing/empty required mesh patch: " + name)
    target = "patch" if name in {"fan_left", "fan_right", "outlet"} else "wall"
    if found[name][1] != target:
        raise SystemExit("Incorrect mesh patch type: " + name)
for name, (count, _) in found.items():
    if name not in expected and count:
        raise SystemExit("Unexpected nonempty patch (fluid selection/leak risk): " + name)
report = Path("log.checkMesh").read_text()
if not re.search(r"Number of regions:\s+1\b", report):
    raise SystemExit("Single connected fluid region not established by checkMesh")
print("Seven nonempty named patches and one connected region confirmed.")
'''


def validate_config(config, cfm, level_name):
    if (config["openfoam_distribution"], config["openfoam_version"], config["solver"]) != ("OpenCFD", "v2412", "simpleFoam"):
        raise ValueError("Generator supports only OpenCFD v2412 simpleFoam")
    if config["geometry_units"] != "m" or tuple(config["patches"]) != PATCHES:
        raise ValueError("Expected metre-scale geometry and the seven documented patches")
    if config["thermal"]["enabled"] or config["scope"] != "sealed_internal_flow_benchmark":
        raise ValueError("Generator implements only the sealed isothermal benchmark")
    if not math.isfinite(cfm) or cfm <= 0:
        raise ValueError("Per-fan CFM must be positive and finite")
    if level_name not in config["mesh_levels"]:
        raise ValueError("Unknown mesh level")
    for value in (config["air"]["kinematic_viscosity_m2_s"], config["air"]["reference_density_kg_m3"],
                  config["turbulence"]["intensity"], config["turbulence"]["length_scale_m"]):
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Air and turbulence assumptions must be finite and positive")


def generate(config_path, geometry_dir, output_dir, cfm, level_name):
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config, cfm, level_name)
    if output_dir.exists():
        raise ValueError(f"Refusing to overwrite existing case: {output_dir}")
    patches, geometry = inspect_geometry(geometry_dir, config)
    q = cfm * CFM_TO_M3_S
    files, initialization = field_files(q, config, geometry)
    level = config["mesh_levels"][level_name]
    files.update({
        "constant/triSurface/fluid_boundary.stl": combined_stl(patches),
        "constant/transportProperties": foam_header("transportProperties") + "transportModel Newtonian;\nnu [0 2 -1 0 0 0 0] " + fmt(config["air"]["kinematic_viscosity_m2_s"]) + ";\n",
        "constant/turbulenceProperties": foam_header("turbulenceProperties") + "simulationType RAS;\nRAS { RASModel kOmegaSST; turbulence on; printCoeffs on; }\n",
        "system/blockMeshDict": block_mesh(config, level),
        "system/snappyHexMeshDict": snappy(config, level),
        "system/controlDict": control(config),
        "system/fvSchemes": foam_header("fvSchemes") + FV_SCHEMES,
        "system/fvSolution": foam_header("fvSolution") + FV_SOLUTION,
        "Allrun": ALLRUN,
        "verify_mesh.py": VERIFY_MESH,
        "case.foam": "",
    })
    manifest = {"status": "generated_not_meshed_or_solved", "distribution": "OpenCFD", "version": "v2412",
                "scope": config["scope"], "per_fan_cfm_assumed": cfm, "per_fan_m3_s_assumed": q,
                "total_m3_s_assumed": 2*q, "mesh_level": level_name, "mesh_settings": level,
                "inputs": config, "geometry": geometry, "initialization_assumptions": initialization,
                "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "inputs_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
                "generated_file_sha256": {name: hashlib.sha256(body.encode()).hexdigest() for name, body in files.items()}}
    files["case_manifest.json"] = json.dumps(manifest, indent=2) + "\n"
    for name, body in files.items():
        path = output_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8", newline="\n")
    (output_dir / "Allrun").chmod(0o755)
    return manifest


def main():
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cfm", type=float, required=True, help="Assumed delivered CFM per fan")
    parser.add_argument("--level", choices=("coarse", "medium", "fine"), default="coarse")
    parser.add_argument("--inputs", type=Path, default=base / "inputs.json")
    parser.add_argument("--geometry", type=Path, help="Folder containing the seven patch STLs in metres")
    parser.add_argument("--output", type=Path, help="New case directory; existing directories are never overwritten")
    args = parser.parse_args()
    config = json.loads(args.inputs.read_text(encoding="utf-8"))
    geometry_dir = args.geometry or args.inputs.parent / config["geometry_directory"]
    output = args.output or base / "cases" / "OpenCFD_v2412" / f"q{args.cfm:g}_{args.level}"
    try:
        manifest = generate(args.inputs, geometry_dir, output, args.cfm, args.level)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, f"Case preparation stopped: {error}\n")
    print(f"Prepared {output.resolve()}")
    print(f"Per fan: {manifest['per_fan_m3_s_assumed']:.12g} m3/s assumed; OpenCFD v2412 required.")
    print("No mesher or solver was executed. Allrun is an explicit future action.")


if __name__ == "__main__":
    main()
