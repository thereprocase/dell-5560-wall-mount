"""Offline STEP assembly placement and overlap validation using FreeCAD Python.

Run with C:/Program Files/FreeCAD 1.1/bin/python.exe. Family-level volume
integration checks live in geometry_validation.json; this checks all installed
occurrences geometrically without repeating tessellation work.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import traceback

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "fusion" / "output" / "native"


def bounds(shape):
    b = shape.BoundBox
    return [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax]


def difference(a, b):
    shape = a.cut(b)
    return {"volume_mm3": abs(shape.Volume), "solids": len(shape.Solids),
            "valid": shape.isNull() or shape.isValid()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assembly", type=Path, default=OUT / "assembly.step")
    parser.add_argument("--report", type=Path, default=OUT / "assembly_geometry_validation.json")
    args = parser.parse_args()
    tolerance = 1e-3
    bounds_tolerance = 1e-5
    reference_path = ROOT / "geometry_validation.json"
    report = {"created_utc": datetime.now(timezone.utc).isoformat(),
              "freecad_version": App.Version(), "occt_version": Part.OCC_VERSION,
              "assembly_path": str(args.assembly), "boolean_tolerance_mm3": tolerance,
              "bounds_tolerance_mm": bounds_tolerance, "matches": {},
              "overlap_checks": [], "new_overlaps": [], "errors": [], "passed": False,
              "scope": "Installed solid geometry and overlaps; STEP does not preserve or verify Fusion joints."}
    try:
        reference = json.loads(reference_path.read_text())
        report["reference_sha256"] = hashlib.sha256(reference_path.read_bytes()).hexdigest()
        report["assembly_sha256"] = hashlib.sha256(args.assembly.read_bytes()).hexdigest()
        assembly = Part.read(str(args.assembly))
        solids = assembly.Solids
        report["assembly_valid"] = assembly.isValid()
        report["assembly_solids"] = len(solids)
        report["expected_solids"] = len(reference["parts"])
        sources = {}
        for name in reference["parts"]:
            path = ROOT / "parts" / f"{name}.step"
            source = Part.read(str(path))
            if len(source.Solids) != 1 or not source.isValid():
                raise ValueError(f"Source {name} must contain one valid solid")
            sources[name] = source.Solids[0]
        matched = {}
        unmatched = set(range(len(solids)))
        missing_sources = []
        for name, source in sources.items():
            sb = bounds(source)
            candidates = []
            for index in unmatched:
                native = solids[index]
                error = max(abs(a - b) for a, b in zip(bounds(native), sb))
                if error <= bounds_tolerance:
                    centroid_error = (native.CenterOfMass - source.CenterOfMass).Length
                    candidates.append((centroid_error, error, index))
            if not candidates:
                missing_sources.append(name)
                continue
            candidates.sort()
            centroid_error, bound_error, index = candidates[0]
            if len(candidates) > 1:
                raise ValueError(f"Ambiguous bounding-box assignment for {name}: {candidates}")
            unmatched.remove(index)
            native = solids[index]
            forward, reverse = difference(native, source), difference(source, native)
            valid = native.isValid()
            symmetric = forward["volume_mm3"] + reverse["volume_mm3"]
            item = {"native_solid_index": index, "native_valid": valid,
                    "native_bounds_mm": bounds(native), "source_bounds_mm": sb,
                    "max_bounds_delta_mm": bound_error, "centroid_distance_mm": centroid_error,
                    "native_volume_mm3": native.Volume, "source_volume_mm3": source.Volume,
                    "native_minus_source": forward, "source_minus_native": reverse,
                    "symmetric_difference_mm3": symmetric,
                    "passed": valid and forward["valid"] and reverse["valid"] and symmetric <= tolerance}
            report["matches"][name] = item
            matched[name] = native
            print(f"{name}: {'PASS' if item['passed'] else 'FAIL'} diff={symmetric:.12g} mm3", flush=True)
        report["unmatched_native_indices"] = sorted(unmatched)
        report["unmatched_source_names"] = missing_sources
        expected = reference["overlaps_mm3"]
        for first, second in itertools.combinations(matched, 2):
            pair = f"{first} / {second}"
            reverse_pair = f"{second} / {first}"
            prior = expected.get(pair, expected.get(reverse_pair, 0))
            try:
                common = matched[first].common(matched[second])
                volume = abs(common.Volume)
                valid = common.isNull() or common.isValid()
                item = {"pair": pair, "native_overlap_mm3": volume,
                        "reference_overlap_mm3": prior, "delta_mm3": volume - prior,
                        "intersection_valid": valid,
                        "expected_design_overlap": prior > tolerance,
                        "new_overlap": prior <= tolerance and volume > tolerance}
                report["overlap_checks"].append(item)
                if item["new_overlap"]:
                    report["new_overlaps"].append(item)
                if not valid:
                    raise ValueError(f"Invalid intersection result: {pair}")
            except Exception as exc:
                report["errors"].append({"operation": f"intersect {pair}",
                                         "message": str(exc), "traceback": traceback.format_exc()})
        report["passed"] = (report["assembly_valid"] and len(solids) == report["expected_solids"]
                            and not unmatched and not missing_sources
                            and all(v["passed"] for v in report["matches"].values())
                            and not report["new_overlaps"] and not report["errors"])
        report["overlap_policy"] = (
            "Flag only intersections exceeding tolerance on pairs absent from the source overlap list. "
            "Existing design-interference volumes and their deltas remain explicitly reported.")
    except Exception as exc:
        report["errors"].append({"operation": "assembly_validation", "message": str(exc),
                                 "traceback": traceback.format_exc()})
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"{'PASS' if report['passed'] else 'FAIL'}: {args.report}", flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
