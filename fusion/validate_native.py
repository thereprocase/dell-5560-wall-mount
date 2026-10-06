"""Compare native Fusion STEP exports with Revision F using offline FreeCAD.

Run: & 'C:/Program Files/FreeCAD 1.1/bin/python.exe' fusion/validate_native.py
Use --local-fan while tray/cap exports remain in their un-tilted source frame.
Reads STEP files without opening documents or accessing Fusion/Onshape APIs.
"""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import traceback

import FreeCAD as App
import Part


ROOT = Path(__file__).resolve().parent.parent
NATIVE_DIR = ROOT / "fusion" / "output" / "native"
SOURCES = {
    "cradle": "02_right_cradle.step",
    "duct": "04_right_fan_duct.step",
    "rail": "08_right_outlet_rail.step",
    "tray": "10_right_fan_tray.step",
    "cap": "06_right_fan_retainer.step",
    "pin": "12_right_push_pin.step",
}


def untilt(shape):
    """Inverse of build_mount.tilt: return to base_geometry fan frame."""
    shape.translate(App.Vector(0, -67, 84))
    shape.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), -45)
    shape.translate(App.Vector(0, 70, -104))


def source_in_export_frame(path, name, local_fan):
    shape = Part.read(str(path))
    if name == "pin":
        # Invert installed_pin(5): untilt, undo (5,146,-103), undo +90 X.
        # Equivalent to onshape/compare_pin_freecad.py's combined translations.
        untilt(shape)
        shape.translate(App.Vector(-5, -146, 103))
        shape.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), -90)
    elif local_fan and name in ("tray", "cap"):
        untilt(shape)
    return shape


def bounds(shape):
    b = shape.BoundBox
    return [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax]


def finite_volume(shape):
    value = shape.Volume
    if not math.isfinite(value):
        raise ValueError(f"Non-finite shape volume: {value}")
    return value


def mesh_volume(shape, deflection):
    """Integrate oriented boundary triangles about their vertex centroid."""
    vertices, triangles = shape.tessellate(deflection)
    if not vertices or not triangles:
        raise ValueError("Tessellation produced no boundary triangles")
    count = len(vertices)
    origin = App.Vector(*(math.fsum(getattr(v, axis) for v in vertices) / count
                          for axis in ("x", "y", "z")))
    points = [v - origin for v in vertices]
    signed = math.fsum(points[a].dot(points[b].cross(points[c]))
                       for a, b, c in triangles) / 6
    if not math.isfinite(signed):
        raise ValueError(f"Non-finite tessellated volume: {signed}")
    return {"signed_volume_mm3": signed, "volume_mm3": abs(signed),
            "vertices": count, "triangles": len(triangles),
            "integration_origin_mm": list(origin)}


def tessellation_fallback(native, source):
    """Independent volume evidence; never overrides failed geometric checks."""
    checks = []
    for deflection in (.01, .001, .0001):
        n = mesh_volume(native, deflection)
        s = mesh_volume(source, deflection)
        checks.append({"deflection_mm": deflection, "native": n, "source": s,
                       "volume_delta_mm3": n["volume_mm3"] - s["volume_mm3"]})
    previous, last = (item["volume_delta_mm3"] for item in checks[-2:])
    tolerance = .001
    last_two_agree = abs(previous) <= tolerance and abs(last) <= tolerance
    convergence = abs(last - previous) <= tolerance
    return {"checks": checks, "delta_tolerance_mm3": tolerance,
            "last_two_deltas_within_tolerance": last_two_agree,
            "last_delta_change_mm3": last - previous,
            "delta_convergence_supported": convergence,
            "supported": last_two_agree and convergence,
            "scope": "Convergence of native/source volume difference; not proof of identical surfaces."}


def compare(name, native_path, source_path, local_fan=False,
            volume_tolerance=1e-3, bounds_tolerance=1e-5):
    result = {
        "native_path": str(native_path), "source_path": str(source_path),
        "comparison_frame": "pin_local" if name == "pin" else (
            "fan_local" if local_fan and name in ("tray", "cap") else "installed_right"),
        "errors": [], "passed": False,
    }
    shapes = {}
    for role, path in (("native", native_path), ("source", source_path)):
        try:
            result[role + "_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            shape = (Part.read(str(path)) if role == "native" else
                     source_in_export_frame(path, name, local_fan))
            if shape.isNull():
                raise ValueError("STEP import produced a null shape")
            shapes[role] = shape
            result[role + "_valid"] = shape.isValid()
            result[role + "_solids"] = len(shape.Solids)
            result[role + "_bounds_mm"] = bounds(shape)
            result[role + "_volume_mm3"] = finite_volume(shape)
        except Exception as exc:
            result["errors"].append({"operation": f"load_and_measure_{role}",
                                     "type": type(exc).__name__, "message": str(exc),
                                     "traceback": traceback.format_exc()})
    if len(shapes) == 2:
        for first, second in (("native", "source"), ("source", "native")):
            label = f"{first}_minus_{second}"
            try:
                difference = shapes[first].cut(shapes[second])
                result[label + "_mm3"] = finite_volume(difference)
                result[label + "_valid"] = difference.isNull() or difference.isValid()
                result[label + "_solids"] = len(difference.Solids)
            except Exception as exc:
                result["errors"].append({"operation": label, "type": type(exc).__name__,
                                         "message": str(exc), "traceback": traceback.format_exc()})
    if not result["errors"]:
        result["volume_delta_mm3"] = result["native_volume_mm3"] - result["source_volume_mm3"]
        result["symmetric_difference_mm3"] = (abs(result["native_minus_source_mm3"]) +
                                                abs(result["source_minus_native_mm3"]))
        result["max_bounds_delta_mm"] = max(abs(a - b) for a, b in
            zip(result["native_bounds_mm"], result["source_bounds_mm"]))
        result["geometric_checks_passed"] = (
            result["native_valid"] and result["source_valid"] and
            result["native_solids"] == result["source_solids"] == 1 and
            result["native_minus_source_valid"] and result["source_minus_native_valid"] and
            result["symmetric_difference_mm3"] <= volume_tolerance and
            result["max_bounds_delta_mm"] <= bounds_tolerance
        )
        result["raw_volume_check_passed"] = abs(result["volume_delta_mm3"]) <= volume_tolerance
        result["volume_validation_method"] = (
            "raw_brep" if result["raw_volume_check_passed"] else "failed")
        if result["geometric_checks_passed"] and not result["raw_volume_check_passed"]:
            try:
                fallback = tessellation_fallback(shapes["native"], shapes["source"])
                result["tessellated_volume_fallback"] = fallback
                if fallback["supported"]:
                    result["volume_validation_method"] = "convergent_tessellation"
                    result["volume_discrepancy_note"] = (
                        "Raw BRep volume check failed. Strict Boolean/bounds/validity checks "
                        "passed, and independent tessellated volume differences support "
                        "acceptance within the recorded tolerance. Raw discrepancy retained.")
            except Exception as exc:
                result["errors"].append({"operation": "tessellated_volume_fallback",
                                         "type": type(exc).__name__, "message": str(exc),
                                         "traceback": traceback.format_exc()})
        result["passed"] = (result["geometric_checks_passed"] and
                            result["volume_validation_method"] != "failed" and
                            not result["errors"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-dir", type=Path, default=NATIVE_DIR)
    parser.add_argument("--report", type=Path, default=NATIVE_DIR / "geometry_validation.json")
    parser.add_argument("--parts", nargs="+", choices=list(SOURCES), default=list(SOURCES))
    parser.add_argument("--local-fan", action="store_true")
    parser.add_argument("--volume-tolerance-mm3", type=float, default=1e-3)
    parser.add_argument("--bounds-tolerance-mm", type=float, default=1e-5)
    args = parser.parse_args()
    for value in (args.volume_tolerance_mm3, args.bounds_tolerance_mm):
        if not math.isfinite(value) or value < 0:
            parser.error("Tolerances must be finite and nonnegative")
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "reference_revision": "F", "freecad_version": App.Version(),
        "occt_version": Part.OCC_VERSION, "local_fan": args.local_fan,
        "volume_tolerance_mm3": args.volume_tolerance_mm3,
        "bounds_tolerance_mm": args.bounds_tolerance_mm,
        "parts": {},
    }
    for name in dict.fromkeys(args.parts):
        result = compare(name, args.native_dir / f"{name}.step", ROOT / "parts" / SOURCES[name],
                         args.local_fan, args.volume_tolerance_mm3, args.bounds_tolerance_mm)
        report["parts"][name] = result
        print(f"{name}: {'PASS' if result['passed'] else 'FAIL'}; "
              f"symmetric_difference_mm3={result.get('symmetric_difference_mm3')}; "
              f"errors={len(result['errors'])}", flush=True)
    report["all_passed"] = all(p["passed"] for p in report["parts"].values())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Report: {args.report}", flush=True)
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
