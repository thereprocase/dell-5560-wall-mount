"""Parameter definitions for the Two-Up Stacked Variant (Precision 5560).

Plain-Python parameter table with zero FreeCAD imports so it can be imported by
standalone analytical geometry and verification tools as well as FreeCAD build
scripts. Every parameter traces to ../../minimalist/build.py,
../DESIGN_GUIDANCE.md, or an explicit ESTIMATE with its arithmetic
shown in comments.
"""
import math

# Ordered parameter specification matching ../../minimalist/build.py:24-78
# so build_two_up.py can populate the TwoUpParameters spreadsheet directly.
PARAMETERS = [
    ('CASE / MEASURE THE CLOSED LAPTOP', None),
    # ../../minimalist/build.py:26
    ('laptopWidth', 344.4, 'mm', 'Actual case width, not screen diagonal'),
    # ../../minimalist/build.py:27
    ('laptopDepth', 230.3, 'mm', 'Base-to-hinge dimension when installed upright'),
    # ../../minimalist/build.py:28
    ('laptopThickness', 20.0, 'mm', 'Maximum closed case thickness'),
    # ../../minimalist/build.py:29
    ('wallGap', 40.0, 'mm', 'Wall to laptop underside at base'),
    # ../../minimalist/build.py:30
    ('padThickness', 2.0, 'mm', 'Separate compliant contact pads; not printed'),
    # ../../minimalist/build.py:31
    ('caseSideGap', 1.0, 'mm', 'Clearance at each laptop side stop'),

    ('TWO-UP STACK / TILT AND PITCH', None),
    # ../DESIGN_GUIDANCE.md:22 — owner target 15 deg stack tilt
    ('tiltDeg', 15.0, 'deg', 'Forward tilt angle of each laptop cradle'),
    # ../DESIGN_GUIDANCE.md:41-42 — ESTIMATE: 222.5 mm tilted rear
    # height + 37.5 mm vertical extraction clearance above hinge = 260.0 mm
    ('stackPitchZ', 260.0, 'mm', 'Vertical Z pitch from Tier 1 base to Tier 2 base'),
    # ../DESIGN_GUIDANCE.md:99-100 — ESTIMATE: Z=160.0 mm split
    # plane gives 160.0 - (-74.0) = 234.0 mm lower arm length (+16 mm brim = 250 mm)
    ('lowerArmTopZ', 160.0, 'mm', 'Horizontal split plane between lower and upper arm'),
    # ../DESIGN_GUIDANCE.md:103-104 — ESTIMATE: Z=395.0 mm top of
    # upper arm gives 395.0 - 160.0 = 235.0 mm upper arm length (+16 mm brim = 251 mm)
    ('upperArmTopZ', 395.0, 'mm', 'Top Z coordinate of upper stacking arm'),
    # ../../minimalist/build.py:500 — lower fan hanger tail reaches Z=-74.0 mm
    ('lowerArmBottomZ', -74.0, 'mm', 'Bottom Z coordinate of lower arm fan tail'),

    ('STRUCTURE / PRINTED ARMS', None),
    # ../../minimalist/build.py:33
    ('armThickness', 12.0, 'mm', 'Main arm section, inboard of the flat print face'),
    # ../../minimalist/build.py:34
    ('sideLip', 3.0, 'mm', 'Thickness of low lateral retention cheek'),
    # ../DESIGN_GUIDANCE.md:187 — ESTIMATE: widened from 6.0 mm
    # (../../minimalist/build.py:35) to 10.0 mm to resist 7.6 N 15-deg thrust
    ('frontLip', 10.0, 'mm', 'Widened front retaining tine thickness for 15-deg tilt'),
    # ../../minimalist/build.py:36
    ('tineHeight', 40.0, 'mm', 'Laptop lift required along cradle axis before removal'),
    # ../../minimalist/build.py:37
    ('wallBoltDiameter', 7.2, 'mm', 'Clearance for the existing wall-anchor class'),
    # ../../minimalist/build.py:38
    ('wallPadDepth', 8.0, 'mm', 'Wall fastener pad thickness'),
    # ../../minimalist/build.py:39
    ('wallPadHeight', 32.0, 'mm', 'Wall pad height; M1.1 reinforced height'),
    # ../../minimalist/build.py:40
    ('wallGussetWeb', 6.0, 'mm', 'Paired webs beside each bolt opening'),
    # ../../minimalist/build.py:41
    ('wallGussetRise', 16.0, 'mm', 'Tapered web reach beyond the wall pad face'),
    # ../DESIGN_GUIDANCE.md:155-158 — ESTIMATE: bolts at local
    # z=18.0 mm and z=144.0 mm inside each arm segment (126.0 mm spacing)
    ('armBoltLowZ', 18.0, 'mm', 'Lower wall bolt Z relative to tier base'),
    ('armBoltHighZ', 144.0, 'mm', 'Upper wall bolt Z relative to tier base'),

    ('FIT / REMOVABLE HARDWARE AND SPLICE', None),
    # ../../minimalist/build.py:43
    ('fitClearance', 0.3, 'mm', 'Nominal clearance at mating surfaces'),
    # ../../minimalist/build.py:44
    ('carriageThickness', 4.0, 'mm', 'Fan, dam, and splice attachment cheek thickness'),
    # ../../minimalist/build.py:45
    ('keyWidth', 8.0, 'mm', 'Two-rung key width, along Y'),
    # ../../minimalist/build.py:46
    ('keyHeight', 5.0, 'mm', 'Two-rung key tongue height'),
    # ../../minimalist/build.py:47
    ('keyPlate', 3.0, 'mm', 'Key connecting plate thickness'),
    # ../../minimalist/build.py:48
    ('keeperDiameter', 3.0, 'mm', 'Non-load-bearing withdrawal keeper shaft'),
    # ../../minimalist/build.py:49
    ('keeperHead', 2.4, 'mm', 'Pin button thickness'),
    # ../../minimalist/build.py:50
    ('retentionInterference', 0.2, 'mm', 'Intentional diametral crown interference'),
    # ../DESIGN_GUIDANCE.md:101-105 — ESTIMATE: four-rung structural
    # splice key straddling the Z=160.0 mm arm split (rungs at Z=130, 154, 166, 190 mm)
    ('spliceKeyWidth', 14.0, 'mm', 'Widened splice key tongue width along Y'),
    ('spliceKeyPlate', 4.0, 'mm', 'Thickened splice key side plate along X'),
    ('spliceSpanZ', 60.0, 'mm', 'Center-to-center Z span across the 4 splice rungs'),

    ('FANS / TWO OPEN CRADLES', None),
    # ../../minimalist/build.py:52
    ('fanWidth', 120.0, 'mm', 'Square fan envelope width'),
    # ../../minimalist/build.py:53
    ('fanThickness', 27.0, 'mm', 'Measured fan envelope; default accepts 25-27 mm'),
    # ../../minimalist/build.py:54
    ('fanFrameWall', 3.0, 'mm', 'Open cradle rails and grille base thickness'),
    # ../../minimalist/build.py:55
    ('grilleBar', 2.4, 'mm', 'Two diagonal intake-guard bars'),
    # ../../minimalist/build.py:56
    ('fanCenterY', 65.0, 'mm', 'Fan outlet-plane center from wall'),
    # ../../minimalist/build.py:57
    ('fanCenterZ', -60.0, 'mm', 'Fan outlet-plane center below the laptop'),
    # ../../minimalist/build.py:58
    ('capThickness', 3.0, 'mm', 'Removable front retainer thickness'),
    # ../../minimalist/build.py:59
    ('capPinDiameter', 4.0, 'mm', 'Front retainer pin shaft'),

    ('LADDER / AIRFLOW DAMS AND CHEEK PANELS', None),
    # ../../minimalist/build.py:61
    ('rungPitch', 12.0, 'mm', 'Positive vertical adjustment step'),
    # ../../minimalist/build.py:62
    ('ladderStart', 50.0, 'mm', 'Lowest rung center above the shelf'),
    # ../../minimalist/build.py:63
    ('damIndex', 8, '', 'Lower engaged rung: integer 0-8; match both sides'),
    # ../../minimalist/build.py:64
    ('damSkin', 1.6, 'mm', 'Open airflow deflector skin'),
    # ../../minimalist/build.py:65
    ('outletGap', 12.0, 'mm', 'Nominal top opening behind the case'),
    # ../../minimalist/build.py:66
    ('centerSeam', 0.6, 'mm', 'Clear gap between left and right dam halves'),
    # ../DESIGN_GUIDANCE.md:113,124 — ESTIMATE: 2.4 mm outer cheek
    # skin thickness clipping into arm windows to enclose the side plenum
    ('cheekThickness', 2.4, 'mm', 'Flat side-plenum cheek panel thickness'),
    # ../DESIGN_GUIDANCE.md:113 — ESTIMATE: 210.3 mm height matching
    # baseline armHeight so each cheek panel covers one tier and fits <256 mm bed
    ('cheekHeight', 210.3, 'mm', 'Vertical height of one single-tier side cheek panel'),

    ('DERIVED / FOLLOW THE INPUTS', None),
    # ../../minimalist/build.py:68 — resolves to 210.3 mm for 5560
    ('armHeight', '=min(max(laptopDepth - 22 mm + padThickness;186 mm);220 mm)', 'mm',
     'Single-tier reference arm height (210.3 mm on 5560)'),
    # ../../minimalist/build.py:69 — resolves to 176.2 mm
    ('armOriginX', '=laptopWidth / 2 + caseSideGap + sideLip', 'mm',
     'Right outboard print face; mirrored for left'),
    # ../../minimalist/build.py:70 — resolves to 38.0 mm
    ('rearFace', '=wallGap - padThickness', 'mm', 'Rear pad seat at base (Z=0)'),
    # ../../minimalist/build.py:71 — resolves to 62.0 mm
    ('frontFace', '=wallGap + laptopThickness + padThickness', 'mm',
     'Front pad seat upright baseline'),
    # ../../minimalist/build.py:72 — resolves to 31.0 mm
    ('ladderY', '=rearFace - 7 mm', 'mm', 'Rung/key center line'),
    # ../../minimalist/build.py:73 — resolves to 24.0 mm
    ('keySeparation', '=2 * rungPitch', 'mm',
     'Two engaged rungs separated by one free rung'),
    # ../../minimalist/build.py:74 — resolves to 146.0 mm
    ('damAttachZ', '=ladderStart + damIndex * rungPitch', 'mm',
     'Lower engaged rung center'),
    # ../../minimalist/build.py:75 — resolves to 52.3 mm
    ('damLift', '=laptopDepth - 178 mm', 'mm',
     'Preset-dependent rise above the ladder'),
    # ../../minimalist/build.py:76 — resolves to 198.3 mm
    ('damStartZ', '=damAttachZ + damLift', 'mm',
     'Start of the 45-degree-or-steeper deflector'),
    # ../../minimalist/build.py:77 — resolves to 76.6 mm
    ('fanOffsetX', '=fanWidth / 2 + armThickness + carriageThickness + 2 * fitClearance',
     'mm', 'Fan center inboard of each arm'),
]


def make_params() -> dict:
    """Return a plain-Python dictionary of all direct and derived parameters."""
    p = {}
    for entry in PARAMETERS:
        if entry[1] is None or isinstance(entry[1], str):
            continue
        p[entry[0]] = float(entry[1])

    # Derived parameters matching ../../minimalist/build.py:68-77
    p['armHeight'] = min(max(p['laptopDepth'] - 22.0 + p['padThickness'], 186.0), 220.0)
    p['armOriginX'] = p['laptopWidth'] / 2.0 + p['caseSideGap'] + p['sideLip']
    p['rearFace'] = p['wallGap'] - p['padThickness']
    p['frontFace'] = p['wallGap'] + p['laptopThickness'] + p['padThickness']
    p['ladderY'] = p['rearFace'] - 7.0
    p['keySeparation'] = 2.0 * p['rungPitch']
    p['damAttachZ'] = p['ladderStart'] + p['damIndex'] * p['rungPitch']
    p['damLift'] = p['laptopDepth'] - 178.0
    p['damStartZ'] = p['damAttachZ'] + p['damLift']
    p['fanOffsetX'] = (
        p['fanWidth'] / 2.0
        + p['armThickness']
        + p['carriageThickness']
        + 2.0 * p['fitClearance']
    )

    # Trigonometric and 15-deg tilted envelope values from
    # ../DESIGN_GUIDANCE.md:33-53
    theta = math.radians(p['tiltDeg'])
    p['sinTilt'] = math.sin(theta)
    p['cosTilt'] = math.cos(theta)
    p['tanTilt'] = math.tan(theta)

    # Single tilted case vertical height: D*cos(15) + T*sin(15) = 227.63 mm
    p['tiltedCaseHeightZ'] = (
        p['laptopDepth'] * p['cosTilt'] + p['laptopThickness'] * p['sinTilt']
    )
    # Single tilted case horizontal projection: D*sin(15) + T*cos(15) = 78.92 mm
    p['tiltedCaseProjY'] = (
        p['laptopDepth'] * p['sinTilt'] + p['laptopThickness'] * p['cosTilt']
    )
    # Plenum wedge depth at hinge (Z = D*cos(15) = 222.45 mm): 40.0 + 230.3*sin(15) = 99.61 mm
    p['plenumHingeY'] = p['wallGap'] + p['laptopDepth'] * p['sinTilt']
    # Total depth off wall at front lip: 40.0 + 78.92 + 2.0 + 10.0 = 130.92 mm
    # (126.92 mm with 6 mm lip, 130.92 mm with widened 10 mm frontLip per Section 5)
    p['tiltedFrontOuterY'] = (
        p['wallGap'] + p['tiltedCaseProjY'] + p['padThickness'] + p['frontLip']
    )
    # Vertical height of each split arm stage
    p['lowerArmSpanZ'] = p['lowerArmTopZ'] - p['lowerArmBottomZ']  # 234.0 mm
    p['upperArmSpanZ'] = p['upperArmTopZ'] - p['lowerArmTopZ']     # 235.0 mm

    # Process constants from ../../minimalist/reports/release.json:5-17
    # and ../../README.md:99-100
    p['asaDensityGPerCm3'] = 1.05
    p['bedLimitX'] = 256.0
    p['bedLimitY'] = 256.0
    p['bedLimitZ'] = 256.0
    p['brimWidth'] = 8.0

    return p


PARAMS = make_params()
