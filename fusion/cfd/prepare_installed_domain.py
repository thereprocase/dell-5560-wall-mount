"""Offline full-ambient geometry with a vented laptop and four actuator zones.

Geometry surrogate only. Dell blower curves and grille/fin losses are unknown;
this does not authorize or produce an installed cooling/thermal prediction.
Run with the installed FreeCAD Python. Existing sealed benchmarks are preserved.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import traceback

import FreeCAD as App
import Part
import MeshPart

from prepare_geometry import tilt, bounds

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / "fusion" / "output" / "native"
PATCHES = ("printed", "laptop", "noctua", "wall_plane", "ambient_openings")


def fingerprint(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def parameters(metadata):
    values = {}
    for parameter in metadata["parameters"]:
        # Current helper manifest supplies literal mm values; reject expressions
        # rather than silently guessing expression evaluation outside Fusion.
        expression = parameter["expression"].strip()
        if not expression.endswith(" mm"):
            raise ValueError(f"Unsupported helper parameter expression: {expression}")
        values[parameter["name"].removeprefix("CFD_")] = float(expression[:-3])
    return values


def decode_helpers(manifest):
    meta_path, step_path = NATIVE / "cfd_helpers_traced.json", NATIVE / "cfd_helpers_traced.step"
    metadata=json.loads(meta_path.read_text())
    shape=Part.read(str(step_path))
    manifest["inputs"] += [fingerprint(meta_path), fingerprint(step_path)]
    manifest["helper_parameters"]=metadata["parameters"]
    manifest["helper_step_solid_count"]=len(shape.Solids)
    manifest["trace"]=metadata["trace"]
    zones={};laptop=None
    manifest["zone_provenance"]={}
    for role in metadata["roles"]:
        centre=App.Vector(*role["centroid_mm"])
        candidates=[s for s in shape.Solids if (s.CenterOfMass-centre).Length<.001 and abs(s.Volume-role["volume_mm3"])<max(.001,role["volume_mm3"]*1e-6)]
        if len(candidates)!=1:raise ValueError("Exported role mapping failed: "+role["name"])
        body=candidates[0]
        if role["role"]=="laptop_shell":laptop=body
        if role["role"] in ("fan_actuator_zone","porous_interface_zone"):
            side="left" if role["name"].startswith("LH") else "right"
            name=("dell_fan_" if role["role"]=="fan_actuator_zone" else "intake_grille_")+side
            zones[name]=body
            manifest["zone_provenance"][name]={"helper_role":role,"reconstructed_from_native_recipe":False}
    if laptop is None:raise ValueError("Laptop missing")
    manifest["wall_handling"]="Native wall at Y=0 is the domain wall boundary."
    return laptop,zones


def noctua_housing():
    body = Part.makeBox(120, 120, 27, App.Vector(10, 10, -138))
    edges = [edge for edge in body.Edges if len(edge.Vertexes) == 2 and
             abs(edge.Vertexes[0].Point.z-edge.Vertexes[1].Point.z) > 26.9]
    body = body.makeFillet(4, edges)
    body = body.cut(Part.makeCylinder(55, 29, App.Vector(70, 70, -139), App.Vector(0, 0, 1)))
    return tilt(body)


def face_owner(face, obstacles):
    points = [vertex.Point for vertex in face.Vertexes]
    if points and all(abs(p.y) < 1e-6 for p in points):
        return "wall_plane", {"method": "domain_plane"}
    if points and any(all(abs(getattr(p, axis)-coordinate) < 1e-6 for p in points)
                      for axis, coordinate in [("x", -400), ("x", 400), ("y", 450), ("z", -300), ("z", 500)]):
        return "ambient_openings", {"method": "domain_plane"}
    # The mass centroid of a curved face need not lie on that face. Project it
    # back to the trimmed face before testing ownership against obstacle solids.
    projection = face.distToShape(Part.Vertex(face.CenterOfMass))
    point = projection[1][0][0]
    probe = Part.Vertex(point)
    distances = {name: probe.distToShape(body)[0] for name, body in obstacles.items()}
    closest = min(distances, key=distances.get)
    if distances[closest] > 1e-4:
        raise ValueError(f"Boundary face has no obstacle provenance: {distances}")
    candidates = [name for name, distance in distances.items() if distance < 1e-6]
    if len(candidates) > 1:
        # A sample at an interface can touch two bodies. Compare overlapping
        # face area, preserving the entire-face partition without triangle guesses.
        overlap = {name: face.common(obstacles[name]).Area for name in candidates}
        closest = max(overlap, key=overlap.get)
        return closest, {"method": "projected_centroid_and_overlap_area", "distances_mm": distances,
                         "candidate_overlap_areas_mm2": overlap}
    return closest, {"method": "projected_face_centroid", "distances_mm": distances}


def write_stl(path, name, facets, vertices, indices):
    with path.open("w", encoding="ascii", newline="\n") as output:
        output.write(f"solid {name}\n")
        for index in indices:
            points = [vertices[i] for i in facets[index]]
            normal = (points[1]-points[0]).cross(points[2]-points[0])
            if normal.Length <= 1e-15:
                raise ValueError(f"Degenerate facet {index} in {name}")
            normal /= normal.Length
            output.write("  facet normal " + " ".join(f"{v:.15g}" for v in normal) + "\n    outer loop\n")
            for point in points:
                output.write("      vertex " + " ".join(f"{v*.001:.15g}" for v in point) + "\n")
            output.write("    endloop\n  endfacet\n")
        output.write(f"endsolid {name}\n")


def mesh_report(mesh):
    vertices, facets = mesh.Topology
    edges = Counter()
    for ids in facets:
        for a, b in zip(ids, ids[1:]+ids[:1]):
            edges[tuple(sorted((a, b)))] += 1
    intersections = mesh.getSelfIntersections()
    return {"vertices": len(vertices), "triangles": len(facets),
            "boundary_edges": sum(v == 1 for v in edges.values()),
            "nonmanifold_edges": sum(v > 2 for v in edges.values()),
            "mesh_is_solid": mesh.isSolid(), "freecad_self_intersections": len(intersections),
            "freecad_self_intersection_pairs": list(intersections)[:30],
            "independent_solver_surface_check": "Not performed by this script; required before meshing."}


def export_surface(fluid, owners, output, deflection):
    mesh = MeshPart.meshFromShape(Shape=fluid, LinearDeflection=deflection,
                                  AngularDeflection=.15, Relative=False, Segments=True)
    vertices, facets = mesh.Topology
    if mesh.countSegments() != len(fluid.Faces):
        raise ValueError("Mesher face segments do not match BRep face count")
    groups = {name: [] for name in PATCHES}
    for index, owner in enumerate(owners):
        groups[owner].extend(mesh.getSegment(index))
    assigned = [i for group in groups.values() for i in group]
    if len(assigned) != len(facets) or set(assigned) != set(range(len(facets))):
        raise ValueError("Boundary triangle partition is not exact")
    for name, group in groups.items():
        if not group:
            raise ValueError(f"Empty installed-domain patch: {name}")
        write_stl(output / f"{name}.stl", name, facets, vertices, group)
    report = mesh_report(mesh)
    report.update({"triangle_partition_exact": True,
                   "triangles_per_patch": {name: len(group) for name, group in groups.items()},
                   "linear_deflection_mm": deflection, "angular_deflection_radians": .15})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "geometry_installed")
    parser.add_argument("--deflection-mm", type=float, default=.1)
    parser.add_argument("--printed-assembly", type=Path, default=NATIVE / "assembly.step",
                        help="Installed-coordinate printed assembly STEP; default is historic Revision F")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"created_utc": datetime.now(timezone.utc).isoformat(),
              "model": "Full ambient geometry with unmeasured vented-laptop airflow surrogate",
              "geometry_ready": False, "solver_case_ready": False, "physics_results": False,
              "solver_stop_reasons": ["Dell blower pressure-flow curves and RPM are UNKNOWN.",
                                      "Grille and fin resistance are unmeasured.",
                                      "Independent surfaceCheck and volume-mesh quality checks are required."],
              "domain_bounds_mm": [-400, 0, -300, 400, 450, 500],
              "step_units": "millimetres", "stl_units": "metres",
              "inputs": [], "errors": [], "assumptions": [
                  "Laptop internal topology is a surrogate, not a measured Dell internal CFD model.",
                  "Noctua housing rings use source reference envelopes without hub or spokes; actuator zones replace rotor action.",
                  "Four fan markers and the grille marker are NOT impermeable obstacles.",
                  "Finite ambient-domain extents need a domain-size sensitivity check."]}
    try:
        path = args.printed_assembly.resolve()
        printed = Part.read(str(path))
        if not printed.isValid() or len(printed.Solids) != 14:
            raise ValueError("Expected validated 14-solid printed assembly")
        report["inputs"].append(fingerprint(path))
        laptop, zones = decode_helpers(report)
        right_housing = noctua_housing()
        left_housing = right_housing.mirror(App.Vector(), App.Vector(1, 0, 0))
        housings = Part.makeCompound([left_housing, right_housing])
        for side, sign in [("left", -1), ("right", 1)]:
            zone = tilt(Part.makeCylinder(55, 2, App.Vector(70, 70, -125.5), App.Vector(0, 0, 1)))
            if sign < 0:
                zone = zone.mirror(App.Vector(), App.Vector(1, 0, 0))
            zones[f"noctua_fan_{side}"] = zone
        obstacles = {"printed": printed, "laptop": laptop, "noctua": housings}
        fluid = Part.makeBox(800, 450, 800, App.Vector(-400, 0, -300))
        for name, body in obstacles.items():
            fluid = fluid.cut(body)
            if not fluid.isValid():
                raise ValueError(f"Invalid fluid after subtracting {name}")
        components = sorted(fluid.Solids, key=lambda shape: shape.Volume, reverse=True)
        if not components:
            raise ValueError("Empty ambient fluid")
        report["components_before_selection"] = len(components)
        report["excluded_closed_pockets"] = [{"volume_mm3": part.Volume, "bounds_mm": bounds(part)}
                                             for part in components[1:]]
        fluid = components[0].removeSplitter()
        if not fluid.isValid() or len(fluid.Solids) != 1 or not fluid.isClosed():
            raise ValueError("Installed fluid must be one valid closed solid")
        # Remove cached triangulations without translating the BRep through STEP.
        # A prior STEP roundtrip appeared to repair mesh seams but coincident
        # Boolean comparisons failed with near-whole-domain residuals. That
        # roundtrip is explicitly NOT accepted as evidence of equivalence.
        report["rejected_step_roundtrip"] = {
            "source_minus_reimport_mm3": 285463059.11833507,
            "reimport_minus_source_mm3": 285348316.5141635,
            "raw_volume_delta_mm3": 0.01776677370071411,
            "accepted": False,
            "reason": "Coincident Boolean comparison failed; equality unproven."}
        original_volume = fluid.Volume
        original_bounds = bounds(fluid)
        fluid = fluid.cleaned()
        report["triangulation_cache_reset"] = {
            "method": "TopoShape.cleaned(): copy with triangulation removed",
            "raw_volume_delta_mm3": fluid.Volume-original_volume,
            "bounds_unchanged": bounds(fluid) == original_bounds,
            "geometry_conversion": False}
        if not fluid.isValid() or not fluid.isClosed() or len(fluid.Solids) != 1:
            raise ValueError("Triangulation cache reset changed solid validity")
        fluid.exportBrep(str(args.output / "fluid_source.brep"))
        fluid.exportStep(str(args.output / "fluid.step"))
        report["fluid"] = {"valid": True, "closed": True, "connected_solids": 1,
                           "volume_m3": fluid.Volume*1e-9, "faces": len(fluid.Faces),
                           "bounds_mm": bounds(fluid)}
        # Interior probe, within the laptop cavity and away from the actuator,
        # confirms the largest ambient component reaches the laptop interior.
        probe = App.Vector(-111, 45, 175)
        report["laptop_cavity_probe"] = {"point_mm": list(probe),
                                         "inside_selected_ambient_fluid": fluid.isInside(probe, 1e-6, False)}
        if not report["laptop_cavity_probe"]["inside_selected_ambient_fluid"]:
            raise ValueError("Laptop internal cavity is disconnected from selected ambient domain")
        owners = []
        report["boundary_faces"] = []
        for index, face in enumerate(fluid.Faces):
            owner, evidence = face_owner(face, obstacles)
            owners.append(owner)
            report["boundary_faces"].append({"index": index, "patch": owner,
                                              "area_m2": face.Area*1e-6, **evidence})
        report["patches"] = {name: {"faces": owners.count(name),
            "area_m2": sum(f.Area for f, owner in zip(fluid.Faces, owners) if owner == name)*1e-6,
            "file": f"{name}.stl"} for name in PATCHES}
        report["surface_mesh"] = export_surface(fluid, owners, args.output, args.deflection_mm)
        zone_dir = args.output / "zones"
        zone_dir.mkdir(exist_ok=True)
        report["zones"] = {}
        for name, zone in zones.items():
            intersection = zone.common(fluid)
            outside = zone.cut(fluid)
            mesh = MeshPart.meshFromShape(Shape=zone, LinearDeflection=args.deflection_mm,
                                          AngularDeflection=.15, Relative=False)
            vertices, facets = mesh.Topology
            write_stl(zone_dir / f"{name}.stl", name, facets, vertices, range(len(facets)))
            report["zones"][name] = {"file": f"zones/{name}.stl", "valid": zone.isValid(),
                "centroid_mm": list(zone.CenterOfMass), "bounds_mm": bounds(zone),
                "volume_mm3": zone.Volume, "fluid_intersection_mm3": intersection.Volume,
                "fraction_inside_fluid": intersection.Volume/zone.Volume,
                "outside_fluid_mm3": outside.Volume, "not_an_obstacle": True,
                "fully_inside_fluid_within_0_001_mm3": abs(outside.Volume) <= .001,
                "actuator_direction": ([0, 1, 0] if name.startswith("dell") else
                                       [0, -math.sqrt(.5), math.sqrt(.5)] if name.startswith("noctua") else None),
                "mesh": mesh_report(mesh)}
        report["all_zone_volumes_inside_fluid"] = all(z["fully_inside_fluid_within_0_001_mm3"]
                                                      for z in report["zones"].values())
        report["geometry_ready"] = (report["surface_mesh"]["mesh_is_solid"] and
                                    report["surface_mesh"]["boundary_edges"] == 0 and
                                    report["surface_mesh"]["nonmanifold_edges"] == 0 and
                                    report["surface_mesh"]["freecad_self_intersections"] == 0 and
                                    report["all_zone_volumes_inside_fluid"])
    except Exception as exc:
        report["errors"].append({"type": type(exc).__name__, "message": str(exc),
                                 "traceback": traceback.format_exc()})
    (args.output / "geometry_manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report.get(key) for key in ["geometry_ready", "solver_case_ready", "fluid",
                     "surface_mesh", "all_zone_volumes_inside_fluid", "errors"]}, indent=2))
    return 0 if report["geometry_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
