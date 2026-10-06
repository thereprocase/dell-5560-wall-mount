"""Prepare a SIMPLIFIED SEALED INTERNAL FLOW BENCHMARK with offline FreeCAD.

This is not an installed-flow prediction: artificial side seals suppress ambient
leakage. No fan performance, turbulence, heat load or thermal result is assumed.
Run with the installed FreeCAD Python. Default output is cfd/geometry (gap12).
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import traceback

import FreeCAD as App
import Part
import MeshPart

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = Path(__file__).resolve().parent / "geometry"
PATCHES = ("fan_left", "fan_right", "outlet", "laptop_shell", "wall_plane",
           "assumed_side_seals", "printed_or_model_walls")
S = math.sqrt(.5)
FAN_Z = -110
FAN_CENTERS = {"fan_left": (-70, 67 + 6*S, -84 - 6*S),
               "fan_right": (70, 67 + 6*S, -84 - 6*S)}
FAN_OUTWARD = App.Vector(0, S, -S)


def bounds(shape):
    b = shape.BoundBox
    return [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax]


def tilt(shape):
    shape.translate(App.Vector(0, -70, 104))
    shape.rotate(App.Vector(), App.Vector(1, 0, 0), 45)
    shape.translate(App.Vector(0, 67, -84))
    return shape


def right_channel():
    wires = []
    for left, right in [((23, -128), (111, -40)), ((8, -80), (66, -28)),
                        ((4, -35), (42, -10)), ((4, 0), (40, 0))]:
        dy, dz = right[0] - left[0], right[1] - left[1]
        length = math.hypot(dy, dz)
        left = (left[0] + 2*dy/length, left[1] + 2*dz/length)
        right = (right[0] - 2*dy/length, right[1] - 2*dz/length)
        points = [App.Vector(x, *yz) for x, yz in
                  [(3, left), (138, left), (138, right), (3, right)]]
        wires.append(Part.makePolygon(points + points[:1]))
    channel = Part.makeLoft(wires, True, True)
    inlet = tilt(Part.makeCylinder(58, 6, App.Vector(70, 70, FAN_Z), App.Vector(0, 0, 1)))
    return channel.fuse(inlet)


def plenum(gap):
    yz = [(0, 0), (40, 0), (40, 232), (40-gap, 232),
          (40-gap, 226), (4, 198), (0, 196)]
    points = [App.Vector(-180, y, z) for y, z in yz]
    return Part.Face(Part.makePolygon(points + points[:1])).extrude(App.Vector(360, 0, 0))


def laptop():
    body = Part.makeBox(344.4, 20, 230.3, App.Vector(-172.2, 40, 2))
    edges = [e for e in body.Edges if len(e.Vertexes) == 2 and
             abs(e.Vertexes[0].Point.y - e.Vertexes[1].Point.y) > 19.9]
    return body.makeFillet(4, edges)


def obstacles(gap, manifest):
    path = ROOT / "fusion" / "output" / "native" / "assembly.step"
    assembly = Part.read(str(path))
    manifest["inputs"] = [{"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}]
    if len(assembly.Solids) != 14 or not assembly.isValid():
        raise ValueError("Expected valid 14-solid native assembly")
    if gap == 12:
        return assembly
    # Match nominal rails by their source geometry bounds before replacing them.
    keep = list(assembly.Solids)
    replacements = []
    for side, source_name in [("left", "07_left_outlet_rail.step"),
                              ("right", "08_right_outlet_rail.step")]:
        reference = Part.read(str(ROOT / "parts" / source_name))
        indices = [i for i, part in enumerate(keep) if
                   max(abs(a-b) for a, b in zip(bounds(part), bounds(reference))) < 1e-5]
        if len(indices) != 1:
            raise ValueError(f"Cannot uniquely identify {side} nominal rail")
        keep.pop(indices[0])
        variant_path = ROOT / "outlet_gap_variants" / f"{side}_outlet_rail_gap_{gap}mm.step"
        replacement = Part.read(str(variant_path))
        if not replacement.isValid() or len(replacement.Solids) != 1:
            raise ValueError(f"Invalid rail variant: {variant_path}")
        replacements.append(replacement)
        manifest["inputs"].append({"path": str(variant_path),
                                  "sha256": hashlib.sha256(variant_path.read_bytes()).hexdigest()})
    return Part.makeCompound(keep + replacements)


def classify(points, tolerance=1e-5):
    """Disjoint precedence for the benchmark's named planar boundaries."""
    for name, center in FAN_CENTERS.items():
        origin = App.Vector(*center)
        if all(abs((p-origin).dot(FAN_OUTWARD)) <= tolerance for p in points):
            on_side = all(p.x < 0 for p in points) if name == "fan_left" else all(p.x > 0 for p in points)
            if on_side:
                return name
    if all(abs(p.z-232) <= tolerance for p in points):
        return "outlet"
    if all(abs(p.y-40) <= tolerance for p in points):
        return "laptop_shell"
    if all(abs(p.y) <= tolerance for p in points):
        return "wall_plane"
    if all(abs(p.x-180) <= tolerance for p in points) or all(abs(p.x+180) <= tolerance for p in points):
        return "assumed_side_seals"
    return "printed_or_model_walls"


def face_patch(face):
    if not isinstance(face.Surface, Part.Plane):
        return "printed_or_model_walls"
    return classify([vertex.Point for vertex in face.Vertexes])


def mesh_and_export(fluid, out, manifest, deflection):
    mesh = MeshPart.meshFromShape(Shape=fluid, LinearDeflection=deflection,
                                  AngularDeflection=.15, Relative=False)
    vertices, triangles = mesh.Topology
    groups = {name: [] for name in PATCHES}
    edges = Counter()
    normals = {name: App.Vector() for name in PATCHES}
    areas = Counter()
    degenerate = 0
    for indices in triangles:
        points = [vertices[i] for i in indices]
        normal = (points[1]-points[0]).cross(points[2]-points[0])
        area = normal.Length / 2
        if area <= 1e-15:
            degenerate += 1
            continue
        patch = classify(points)
        groups[patch].append((points, normal/normal.Length))
        normals[patch] += normal/2
        areas[patch] += area
        for i, j in zip(indices, indices[1:] + indices[:1]):
            edges[tuple(sorted((i, j)))] += 1
    boundary_edges = sum(count == 1 for count in edges.values())
    nonmanifold_edges = sum(count > 2 for count in edges.values())
    manifest["mesh"] = {"linear_deflection_mm": deflection, "angular_deflection_radians": .15,
                        "vertices": len(vertices), "triangles": len(triangles),
                        "degenerate_triangles": degenerate, "boundary_edges": boundary_edges,
                        "nonmanifold_edges": nonmanifold_edges, "mesh_is_solid": mesh.isSolid(),
                        "closed": not boundary_edges and not nonmanifold_edges and not degenerate,
                        "area_m2": sum(areas.values())*1e-6,
                        "triangle_partition_exact": sum(map(len, groups.values())) == len(triangles)}
    for name, faces in groups.items():
        entry = manifest["boundaries"][name]
        vector = normals[name]
        entry.update({"triangles": len(faces), "mesh_area_m2": areas[name]*1e-6,
                      "area_mean_normal": list(vector/areas[name]) if areas[name] else None,
                      "area_weighted_normal": (list(vector/vector.Length)
                                               if vector.Length > 1e-8*areas[name] else None),
                      "stl_file": f"{name}.stl", "stl_units": "metres"})
        path = out / f"{name}.stl"
        with path.open("w", encoding="ascii", newline="\n") as stream:
            stream.write(f"solid {name}\n")
            for points, normal in faces:
                stream.write("  facet normal " + " ".join(f"{v:.12g}" for v in normal) + "\n    outer loop\n")
                for point in points:
                    stream.write("      vertex " + " ".join(f"{v*.001:.12g}" for v in point) + "\n")
                stream.write("    endloop\n  endfacet\n")
            stream.write(f"endsolid {name}\n")
        entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not manifest["mesh"]["closed"] or not manifest["mesh"]["triangle_partition_exact"]:
        raise ValueError(f"Full surface mesh is not a closed exact partition: {manifest['mesh']}")
    if any(not groups[name] for name in PATCHES):
        raise ValueError(f"Empty boundary patches: {[name for name in PATCHES if not groups[name]]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gap", type=int, choices=(8, 12, 16), default=12)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--deflection-mm", type=float, default=.1)
    args = parser.parse_args()
    if not math.isfinite(args.deflection_mm) or args.deflection_mm <= 0:
        parser.error("Mesh deflection must be positive and finite")
    if args.output is None:
        args.output = DEFAULT_OUT if args.gap == 12 else DEFAULT_OUT.with_name(f"geometry_gap{args.gap}")
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(),
                "benchmark": "SIMPLIFIED SEALED INTERNAL FLOW BENCHMARK",
                "scope_status": "Initial sealed baseline only; does not yet satisfy requested laptop vents and internal-blower model.",
                "missing_from_requested_installed_model": ["Laptop underside vent openings and their resistance",
                    "Two internal Dell blowers and fan performance data", "Internal laptop air paths and hinge exhaust geometry",
                    "Ambient leakage and recirculation domain"],
                "installed_flow_prediction": False, "thermal_results": False,
                "assumptions": ["Artificial side seals suppress lateral ambient leakage.",
                                "Envelope uses two ideal inner ruled ducts and a continuous rear plenum.",
                                "Inlet cylinders represent fluid, not modeled fan blades or fan performance.",
                                "Disconnected enclosed pockets are excluded from the inlet-to-outlet fluid domain.",
                                "The laptop_shell patch labels the full planar Y40 benchmark boundary, including assumed continuation beyond the actual laptop outline; it is not a full physical thermal shell."],
                "gap_mm": args.gap, "step_units": "millimetres", "stl_units": "metres",
                "freecad_version": App.Version(), "occt_version": Part.OCC_VERSION,
                "boundaries": {name: {"face_indices_zero_based": [], "brep_area_m2": 0.0}
                               for name in PATCHES}, "errors": [], "ready": False}
    try:
        body = right_channel()
        left = body.mirror(App.Vector(), App.Vector(1, 0, 0))
        envelope = body.fuse(left).fuse(plenum(args.gap))
        if not envelope.isValid() or len(envelope.Solids) != 1:
            raise ValueError("Initial benchmark envelope is not one valid connected solid")
        fluid = envelope.cut(obstacles(args.gap, manifest)).cut(laptop())
        if not fluid.isValid() or not fluid.Solids:
            raise ValueError("Obstacle subtraction produced invalid or empty fluid")
        components = sorted(fluid.Solids, key=lambda part: part.Volume, reverse=True)
        manifest["connected_components_before_selection"] = len(components)
        manifest["excluded_disconnected_pockets"] = [
            {"volume_mm3": part.Volume, "bounds_mm": bounds(part)} for part in components[1:]]
        fluid = components[0].removeSplitter()
        if not fluid.isValid() or len(fluid.Solids) != 1 or not fluid.isClosed():
            raise ValueError("Selected flow domain is not one closed valid solid")
        for index, face in enumerate(fluid.Faces):
            entry = manifest["boundaries"][face_patch(face)]
            entry["face_indices_zero_based"].append(index)
            entry["brep_area_m2"] += face.Area*1e-6
        manifest.update({"valid": True, "solids": 1, "connected": True, "closed_brep": True,
                         "volume_m3": fluid.Volume*1e-9, "bounds_mm": bounds(fluid),
                         "surface_faces": len(fluid.Faces), "brep_surface_area_m2": fluid.Area*1e-6,
                         "face_partition_exact": sum(len(v["face_indices_zero_based"])
                                                     for v in manifest["boundaries"].values()) == len(fluid.Faces),
                         "fan_centers_m": {key: [v*.001 for v in center] for key, center in FAN_CENTERS.items()},
                         "fan_inlet_outward_normal": list(FAN_OUTWARD),
                         "fan_flow_into_domain_normal": [0, -S, S], "outlet_outward_normal": [0, 0, 1]})
        fluid.exportStep(str(args.output / "fluid.step"))
        manifest["fluid_step_sha256"] = hashlib.sha256((args.output / "fluid.step").read_bytes()).hexdigest()
        mesh_and_export(fluid, args.output, manifest, args.deflection_mm)
        manifest["boundaries"]["assumed_side_seals"]["outward_normals"] = [[-1, 0, 0], [1, 0, 0]]
        manifest["boundaries"]["assumed_side_seals"]["normal_note"] = "Opposite seals have cancelling area vectors; no single normal describes this patch."
        manifest["ready"] = manifest["face_partition_exact"]
    except Exception as exc:
        manifest["errors"].append({"type": type(exc).__name__, "message": str(exc),
                                   "traceback": traceback.format_exc()})
    (args.output / "geometry_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest.get(key) for key in
                      ("ready", "solids", "surface_faces", "volume_m3", "mesh", "errors")}, indent=2))
    return 0 if manifest["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
