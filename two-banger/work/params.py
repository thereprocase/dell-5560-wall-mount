"""Parameters for the Two-Banger 5560 Rack (two Dell 5560s, two 140 mm fans).

Greenfield back-to-back A-frame desk-standing rack. Every dimension is in
millimetres (angles in degrees) and traces to the design brief summarised in two-banger/README.md
or explicit design choices recorded in README.md.
"""
import math

PARAMETERS = [
    ('LAPTOP ENVELOPE (DELL PRECISION 5560)', None),
    ('laptopWidth', 344.4, 'mm', 'Closed laptop width along X'),
    ('laptopDepth', 230.3, 'mm', 'Closed laptop depth along tilted axis'),
    ('laptopThickness', 20.0, 'mm', 'Closed laptop thickness'),
    ('caseSideGap', 0.5, 'mm', 'Clearance per side between laptop and end frame'),
    ('cradleClearance', 0.5, 'mm', 'Clearance between laptop and cradle rails/lips'),

    ('FANS (TWO 140 MM CASE FANS)', None),
    ('fanSize', 140.0, 'mm', 'Square 140 mm fan outer width/depth'),
    ('fanThickness', 25.0, 'mm', 'Standard 140 mm fan thickness'),
    ('fanHolePitch', 124.5, 'mm', 'Mounting hole square pitch'),
    ('fanHoleDiameter', 4.3, 'mm', 'Fan mounting hole clearance diameter'),
    ('fanCenterX', 74.5, 'mm', 'Fan center X offset from rack centerline (clears center flange)'),
    ('fanClearance', 0.5, 'mm', 'Clearance between fan frame and tray flanges'),

    ('A-FRAME RACK GEOMETRY', None),
    ('tiltDeg', 14.0, 'deg', 'Inward A-frame tilt angle from vertical'),
    ('deskClearanceZ', 16.0, 'mm', 'Open intake air gap below fan tray deck'),
    ('trayDeckThickness', 5.0, 'mm', 'Fan tray bottom deck thickness'),
    ('trayFlangeHeight', 14.0, 'mm', 'Fan tray perimeter stiffening flange height'),
    ('trayFlangeThickness', 4.0, 'mm', 'Fan tray perimeter flange thickness'),
    ('plenumBaseHalfY', 71.0, 'mm', 'Half-width of central plenum at laptop base'),
    ('endFrameThickness', 6.0, 'mm', 'Outer wall thickness of each end frame'),
    ('railInboardDepth', 12.5, 'mm', 'Inboard support rail width (clears intake vents)'),
    ('spineWidth', 14.0, 'mm', 'Width of tilted A-frame spine behind laptop underside'),
    ('outerLipHeight', 24.0, 'mm', 'Bottom outer retention lip height along laptop axis'),
    ('endFrameTopZ', 228.0, 'mm', 'Top Z height of end frame (fits 256 mm bed w/ 8 mm brim)'),

    ('FASTENERS & BED LIMITS', None),
    ('fitClearance', 0.2, 'mm', 'Assembly clearance at tray/frame joints'),
    ('m4ClearanceDia', 4.5, 'mm', 'M4 screw clearance hole diameter'),
    ('m4InsertDia', 5.6, 'mm', 'M4 heat-set insert pilot diameter'),
    ('petgDensity', 1.27, 'g/cm3', 'PETG nominal density for mass estimates'),
    ('bedLimit', 256.0, 'mm', 'Bambu P1S build volume cube limit'),
    ('brimWidth', 8.0, 'mm', 'Outer brim width per side (16 mm total XY allowance)'),
]


def get_params() -> dict:
    p = {e[0]: float(e[1]) for e in PARAMETERS if e[1] is not None}
    theta = math.radians(p['tiltDeg'])
    p['sinTilt'] = math.sin(theta)
    p['cosTilt'] = math.cos(theta)
    p['tanTilt'] = math.tan(theta)
    p['innerWallX'] = p['laptopWidth'] / 2.0 + p['caseSideGap']        # 172.7 mm
    p['outerWallX'] = p['innerWallX'] + p['endFrameThickness']          # 182.7 mm
    p['trayHalfSpanX'] = p['innerWallX'] - p['fitClearance']            # 172.5 mm
    p['fanDeckTopZ'] = p['deskClearanceZ'] + p['trayDeckThickness']     # 21.0 mm
    p['laptopBaseZ'] = p['fanDeckTopZ'] + p['fanThickness'] + 1.0       # 47.0 mm
    return p


PARAMS = get_params()
