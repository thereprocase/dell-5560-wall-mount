"""Standalone verification script for the Two-Up Stacked Variant.

Run with plain Python:
    python3 two-up/work/check.py

Computes oriented bounding boxes, solid volumes, and ASA masses (at 1.05 g/cm3)
from the analytical 2D prism definitions in geometry.py, checks that every part
fits inside the Bambu P1S 256 x 256 x 256 mm build volume including an 8.0 mm
outer brim on all four bed edges (16.0 mm total XY allowance, reducing the net
printable XY envelope to 240.0 x 240.0 mm), compares against measured.json if
present, and exits nonzero if any check fails.
"""
from pathlib import Path
import json
import sys
from params import PARAMS
from geometry import compute_all_parts


def check_all(p: dict = PARAMS) -> int:
    parts = compute_all_parts(p)
    measured_path = Path(__file__).resolve().parent / 'measured.json'
    measured_data = (
        json.loads(measured_path.read_text(encoding='utf-8')).get('parts', {})
        if measured_path.exists()
        else {}
    )

    bed_x = p['bedLimitX']      # 256.0 mm
    bed_y = p['bedLimitY']      # 256.0 mm
    bed_z = p['bedLimitZ']      # 256.0 mm
    brim = p['brimWidth']       # 8.0 mm
    # An 8.0 mm brim surrounds the outer perimeter on both minimum and maximum
    # edges of X and Y (matching ../../minimalist/export.py:112 where bounds
    # must stay within [8.0, 248.0] mm on a 256.0 mm bed).
    brim_allowance_xy = 2.0 * brim  # 16.0 mm total per horizontal axis
    max_part_x = bed_x - brim_allowance_xy  # 240.0 mm
    max_part_y = bed_y - brim_allowance_xy  # 240.0 mm
    max_part_z = bed_z                      # 256.0 mm

    print("Bambu P1S Build-Volume & Brim Verification — Precision 5560 Two-Up Variant")
    print("=" * 128)
    print(
        f"Printer bed limit   : {bed_x:.1f} x {bed_y:.1f} x {bed_z:.1f} mm\n"
        f"Brim allowance      : {brim:.1f} mm outer brim on all sides -> "
        f"+{brim_allowance_xy:.1f} mm to X and Y footprints "
        f"(part XY must be <= {max_part_x:.1f} x {max_part_y:.1f} mm, Z <= {max_part_z:.1f} mm)\n"
        f"Material density    : {p['asaDensityGPerCm3']:.2f} g/cm3 (Bambu ASA, 100% rectilinear)\n"
    )

    header = (
        f"{'Part Name':<28} | {'Footprint XY (mm)':<17} | {'With 8mm Brim':<17} | "
        f"{'Height Z':>8} | {'Est Vol':>9} | {'Est Mass':>8} | {'BRep Mass':>9} | {'Delta%':>7} | {'Status':<6}"
    )
    print(header)
    print("-" * len(header))

    total_vol_cm3 = 0.0
    total_mass_g = 0.0
    total_brep_mass_g = 0.0
    coupon_vol_cm3 = 0.0
    coupon_mass_g = 0.0
    coupon_brep_mass_g = 0.0
    failures = []
    over_5pct = []

    for name, info in parts.items():
        fx = info['footprint_x_mm']
        fy = info['footprint_y_mm']
        fz = info['height_z_mm']
        bx = fx + brim_allowance_xy
        by = fy + brim_allowance_xy
        vol_cm3 = info['volume_cm3']
        mass_g = info['mass_g']

        fits_xy = (bx <= bed_x + 1e-6 and by <= bed_y + 1e-6) or (
            by <= bed_x + 1e-6 and bx <= bed_y + 1e-6
        )
        fits_z = fz <= bed_z + 1e-6
        fits_vol = vol_cm3 > 0.0
        passed = fits_xy and fits_z and fits_vol
        status = "PASS" if passed else "FAIL"
        if not passed:
            failures.append(name)

        m_entry = measured_data.get(name)
        if m_entry:
            brep_mass = float(m_entry['mass_g'])
            pct_diff = ((mass_g - brep_mass) / brep_mass) * 100.0
            brep_str = f"{brep_mass:7.2f}g"
            pct_str = f"{pct_diff:+6.2f}%"
            if abs(pct_diff) > 5.0:
                over_5pct.append((name, mass_g, brep_mass, pct_diff))
        else:
            brep_mass = 0.0
            brep_str = "     N/A"
            pct_str = "    N/A"

        if name == '00_fit_coupon':
            coupon_vol_cm3 += vol_cm3
            coupon_mass_g += mass_g
            coupon_brep_mass_g += brep_mass
        else:
            total_vol_cm3 += vol_cm3
            total_mass_g += mass_g
            total_brep_mass_g += brep_mass

        fp_str = f"{fx:6.1f} x {fy:6.1f}"
        brim_str = f"{bx:6.1f} x {by:6.1f}"
        print(
            f"{name:<28} | {fp_str:<17} | {brim_str:<17} | "
            f"{fz:6.1f}mm | {vol_cm3:7.2f}cm3 | {mass_g:6.2f}g | {brep_str:>9} | {pct_str:>7} | {status:<6}"
        )

    tot_pct = ((total_mass_g - total_brep_mass_g) / total_brep_mass_g * 100.0) if total_brep_mass_g > 0 else 0.0
    coup_pct = ((coupon_mass_g - coupon_brep_mass_g) / coupon_brep_mass_g * 100.0) if coupon_brep_mass_g > 0 else 0.0
    print("-" * len(header))
    print(
        f"{'Two-Up Assembly (01-38)':<28} | {'14 print plates':<17} | {'all <= 256x256 mm':<17} | "
        f"{'<=256mm':>8} | {total_vol_cm3:7.2f}cm3 | {total_mass_g:6.2f}g | "
        f"{total_brep_mass_g:7.2f}g | {tot_pct:+6.2f}% | {'PASS' if not failures else 'FAIL':<6}"
    )
    print(
        f"{'Fit Coupon (00_fit_coupon)':<28} | {'1 coupon plate':<17} | {'<= 256x256 mm':<17} | "
        f"{'<=256mm':>8} | {coupon_vol_cm3:7.2f}cm3 | {coupon_mass_g:6.2f}g | "
        f"{coupon_brep_mass_g:7.2f}g | {coup_pct:+6.2f}% | {'PASS' if '00_fit_coupon' not in failures else 'FAIL':<6}"
    )
    print("=" * 128)
    print(f"Parts exceeding 5.0% difference between analytical estimate and FreeCAD B-rep: {len(over_5pct)}")
    overall = "PASS" if not failures else f"FAIL ({len(failures)} failed: {', '.join(failures)})"
    print(f"OVERALL VERIFICATION RESULT: {overall}")
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(check_all())
