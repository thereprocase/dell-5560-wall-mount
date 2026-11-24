"""Parameters for the Tight Wall-Mount Stacked Two-Banger 5560 Rack.

Both Dell Precision 5560 laptops stand in the same orientation (underside toward
the wall Y=0, hinge up), tilted 10 deg forward and stacked vertically at a
250.0 mm pitch. Two 140 x 140 x 25 mm fans sit at 55 deg at the bottom,
pressurizing the shared rear wall plenum symmetrically.
"""
import math

PARAMETERS = [
    ('LAPTOP ENVELOPE (DELL PRECISION 5560)', None),
    ('laptopWidth', 344.4, 'mm', 'Closed laptop width along X'),
    ('laptopDepth', 230.3, 'mm', 'Closed laptop depth along tilted axis'),
    ('laptopThickness', 20.0, 'mm', 'Closed laptop thickness'),
    ('caseSideGap', 0.5, 'mm', 'Clearance per side between laptop and arm'),
    ('cradleClearance', 0.5, 'mm', 'Clearance between laptop and cradle rails/lips'),

    ('FANS (TWO 140 MM CASE FANS AT 55 DEG)', None),
    ('fanSize', 140.0, 'mm', 'Square 140 mm fan outer width/depth'),
    ('fanThickness', 25.0, 'mm', 'Standard 140 mm fan thickness'),
    ('fanHolePitch', 124.5, 'mm', 'Mounting hole square pitch'),
    ('fanHoleDiameter', 4.3, 'mm', 'Fan mounting hole clearance diameter'),
    ('fanCenterX', 74.5, 'mm', 'Fan center X offset from rack centerline'),
    ('fanCenterY', 60.0, 'mm', 'Fan outlet-plane center Y from wall (Y=0)'),
    ('fanCenterZ', -48.0, 'mm', 'Fan outlet-plane center Z below Tier 1 base'),
    ('fanTiltDeg', 50.0, 'deg', 'Fan tray tilt from horizontal (blows up & wallward)'),
    ('fanClearance', 0.5, 'mm', 'Clearance between fan frame and tray flanges'),

    ('STACKED WALL RACK GEOMETRY', None),
    ('wallGap', 35.0, 'mm', 'Wall (Y=0) to laptop underside at each tier base'),
    ('tiltDeg', 10.0, 'deg', 'Forward tilt of both laptops away from wall'),
    ('stackPitchZ', 212.0, 'mm', 'Vertical pitch from Tier 1 to Tier 2 (tucked 15 mm below Tier 1 hinge)'),
    ('lowerArmBottomZ', -105.0, 'mm', 'Bottom Z of Lower Arm (238 mm tall)'),
    ('armSplitZ', 133.0, 'mm', 'Horizontal split Z between Lower and Upper Arms'),
    ('upperArmTopZ', 371.0, 'mm', 'Top Z of Upper Arm (238 mm tall)'),
    ('armThickness', 8.0, 'mm', 'Outer arm cheek thickness enclosing the wall plenum'),
    ('railInboardDepth', 12.0, 'mm', 'Inboard support rail width (clears intake vents)'),
    ('seatInboardDepth', 26.0, 'mm', 'Inboard extended seat + gusset width at tier base'),
    ('outerLipHeight', 76.2, 'mm', 'Bottom front retention fork height (3.0 in along laptop axis)'),
    ('trayDeckThickness', 12.0, 'mm', 'Solid fan plate thickness'),
    ('trayFlangeHeight', 12.0, 'mm', 'Solid fan plate overall height'),
    ('trayFlangeThickness', 4.0, 'mm', 'Unused legacy flange parameter (solid plate)'),

    ('WALL ANCHORS & FASTENERS', None),
    ('wallPadThickness', 8.0, 'mm', 'Wall mounting pad thickness along Y (Y=0..8 mm)'),
    ('wallPadWidthX', 24.0, 'mm', 'Wall mounting pad width along X'),
    ('wallPadHeightZ', 28.0, 'mm', 'Wall mounting pad height along Z'),
    ('wallBoltDiameter', 7.2, 'mm', 'Wall anchor clearance bore (M6 / 1/4-in lag or toggle)'),
    ('fitClearance', 0.2, 'mm', 'Assembly clearance at tray/arm joints'),
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
    ftheta = math.radians(p['fanTiltDeg'])
    p['sinFan'] = math.sin(ftheta)
    p['cosFan'] = math.cos(ftheta)
    p['innerWallX'] = p['laptopWidth'] / 2.0 + p['caseSideGap']        # 172.7 mm
    p['outerWallX'] = p['innerWallX'] + p['armThickness']               # 180.7 mm
    p['trayHalfSpanX'] = p['innerWallX'] - p['fitClearance']            # 172.5 mm
    return p


PARAMS = get_params()
