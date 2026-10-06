"""Explicit dimensional bindings for Revision F. Local feature dimensions remain editable."""
import ast, math
import FreeCAD as App
import native_ops as N

SPECS=[
('laptopWidth',344.4,'mm','Layout','Moves both complete handed modules symmetrically; reference width'),
('laptopHeight',230.3,'mm','Layout','Drives contraction/throat/outlet heights through formulas'),
('laptopThickness',20,'mm','Layout','Drives bare slot through fit allowance'),
('wallGap',40,'mm','Layout','Laptop rear gap, contact pads, cheeks, rail throat, duct outlet'),
('slotFitAllowance',6,'mm','Fits','Bare slot minus laptop envelope thickness'),
('bareSlot',26,'mm','Fits','Retention slot between lower pad and front tine'),
('tineHeight',94,'mm','Structure','Front tine height, taper and hollow core'),
('wallHoleDiameter',7,'mm','Wall mounting','Bolt shaft and printable roof'),
('wallDriverDiameter',16,'mm','Wall mounting','Driver envelope; corridors retain source extra clearance'),
('wallHoleHalfSpacing',162,'mm','Wall mounting','Absolute bolt-line X; tracks module spacing by default'),
('lowerWallHoleZ',-36,'mm','Wall mounting','Lower bolt and aligned driver corridors'),
('upperWallHoleZ',174,'mm','Wall mounting','Upper bolt and aligned rail corridor'),
('contractionStartZ',198,'mm','Outlet','Start of outlet contraction'),
('throatZ',226,'mm','Outlet','Start of constant outlet width'),
('outletZ',232,'mm','Outlet','Outlet lip height'),
('fanFrameWidth',120,'mm','Fan module','Frame width, tray/deck/cap edges, dovetails and pin centers'),
('fanThicknessNominal',25,'mm','Fan module','Tray depth and cap lower edge/cavities; source allows +2 mm fan tolerance'),
('fanAngle',45,'deg','Fan module','Fan plane, duct inlet, tray/cap/pin placement and service direction'),
('fanCenterY',67,'mm','Fan module','Fan-plane pivot Y'),
('fanCenterZ',-84,'mm','Fan module','Fan-plane pivot Z'),
('ductSkinNominal',2,'mm','Duct','Loft section insets'),
('keyClearance',.3,'mm','Fits','Fixed-key mortise coordinate allowance'),
('trayHorizontalClearance',.3,'mm','Fits','Dovetail flank horizontal clearance'),
('trayRoofClearance',.3,'mm','Fits','Dovetail roof clearance'),
('trayRootClearance',.2,'mm','Fits','Dovetail root clearance'),
('capPinPassageDiameter',4.5,'mm','Fits','Cap pin clearance passage'),
('grilleBarWidth',2.4,'mm','Fan module','Transverse grille bars and center support'),
('laptopLift',105,'mm','Service','Discrete service-path validation lift')]
FORMULAS={'bareSlot':'=laptopThickness + slotFitAllowance',
          'wallHoleHalfSpacing':'=laptopWidth / 2 - 10.2 mm',
          'contractionStartZ':'=laptopHeight - 32.3 mm',
          'throatZ':'=laptopHeight - 4.3 mm','outletZ':'=laptopHeight + 1.7 mm'}

def setup(sheet):
    cells={}
    for c in sheet.getNonEmptyCells():
        alias=sheet.getAlias(c)
        if alias: cells[alias]=c
    row=max([int(c[1:]) for c in sheet.getNonEmptyCells() if c[0]=='B']+[12])+2
    for name,value,unit,category,role in SPECS:
        if name not in cells:
            cell='B'+str(row); sheet.set('A'+str(row),name); sheet.set(cell,('=' if value<0 else '')+str(value)+' '+unit); sheet.setAlias(cell,name); cells[name]=cell; row+=1
        r=cells[name][1:]
        sheet.set('C'+r,category); sheet.set('D'+r,role)
        if name in FORMULAS: sheet.set(cells[name],FORMULAS[name])
    for name in ['pinSocketDiameter','pinShaftDiametralClearance','pinCrownDiametralInterference','pinHeadDiameter','pinHeadHeight','pinHeadChamfer','pinShaftLength','pinCrownHeight','pinTipDiameter','pinSplitWidth','pinSplitStart']:
        if name in cells: sheet.set('C'+cells[name][1:],'Push pin')
    sheet.set('C'+cells['outletGap'][1:],'Outlet'); sheet.set('D'+cells['outletGap'][1:],'8 / 12 / 16 mm; both mirrored rails')
    sheet.setColumnWidth('A',235); sheet.setColumnWidth('B',110); sheet.setColumnWidth('C',125); sheet.setColumnWidth('D',490)
    sheet.Document.recompute()
    return cells

def q(name):
    value=getattr(N.D.getObject('Parameters'),name)
    return N.Expr(value.Value,'(Parameters.'+name+' / (1 mm))')
def angle(name='fanAngle'): return N.Expr(getattr(N.D.getObject('Parameters'),name).Value,'Parameters.'+name)
def dx(): return (q('laptopWidth')-344.4)/2
def df(): return q('fanFrameWidth')-120

def fx(x):
    # Keep the center support at the fan center; move interface edges equally.
    if x<68: return x-df()/2
    if x>73: return x+df()/2
    return x

def sz(z): return z-(q('fanThicknessNominal')-25) if z<=-124 else z

def fy(y): return y

def roof_hole(r,h,base,roof='-X',bridge=1.2):
    x,y,z=base
    if abs(x-162)<1e-8: x=q('wallHoleHalfSpacing')-dx()
    if abs(z+36)<1e-8: z=q('lowerWallHoleZ')
    if abs(z-174)<1e-8: z=q('upperWallHoleZ')
    if abs(r-3.5)<1e-8: r=q('wallHoleDiameter')/2
    elif abs(r-9)<1e-8: r=q('wallDriverDiameter')/2+1
    elif abs(r-10)<1e-8: r=q('wallDriverDiameter')/2+2
    k=r/math.sqrt(2); tip=2*k-bridge/2
    uv=[(k,-k),(tip,-bridge/2),(tip,bridge/2),(k,k)]
    def pt(u,v):
        return (x-u,z+v) if roof=='-X' else ((x+v,z+u) if roof=='+Z' else (x+v,z-u))
    wedge=N.Workplane('XZ',origin=(0,y+h,0)).polyline([pt(u,v) for u,v in uv]).close().extrude(h)
    return cyl(r,h,(x,y,z)).union(wedge)

def cyl(r,h,base,direction=(0,1,0)):
    if N.FAMILY=='FanDuct' and abs(r-2.05)<1e-8: r=q('pinSocketDiameter')/2
    if N.FAMILY=='FanCap' and abs(r-2.25)<1e-8: r=q('capPinPassageDiameter')/2
    if N.FAMILY in ['FanDuct','FanCap'] and base[0] in (5,135): base=(fx(base[0]),base[1],base[2])
    sk=N.circle(r,base,App.Rotation(App.Vector(0,0,1),App.Vector(*direction)))
    return N.extrude(sk,h)

def tongue(cx,y0,y1,clearance=False):
    cx=fx(cx)
    if clearance:
        h=q('trayHorizontalClearance'); r=q('trayRoofClearance'); root=q('trayRootClearance')
        pts=[(cx-1.5-h,-110.1-root),(cx+1.5+h,-110.1-root),(cx+3+h,-108),(cx+3+h,-108+r),(cx-3-h,-108+r),(cx-3-h,-108)]
    else: pts=[(cx-1.5,-110.1),(cx+1.5,-110.1),(cx+3,-108),(cx-3,-108)]
    return N.Workplane('XZ',origin=(0,y1,0)).polyline(pts).close().extrude(y1-y0)

def tilt(s):
    return s.translate((0,-70,104)).rotate((0,0,0),(1,0,0),angle()).translate((0,q('fanCenterY'),q('fanCenterZ')))

def loft_channel(inner=False):
    t=q('ductSkinNominal') if inner else 0
    x0=fx(1)+t; x1=fx(140)-t
    half=math.sqrt(88**2+88**2)/2
    s=N.polygon([(x0,-half+t),(x1,-half+t),(x1,half-t),(x0,half-t)],(0,q('fanCenterY'),q('fanCenterZ')),App.Rotation(App.Vector(1,0,0),float(angle())),'fan inlet section')
    s.setExpression('Placement.Rotation.Angle','Parameters.fanAngle')
    sections=[s]
    # The cradle-side interface is fixed; only the inlet follows fan width.
    x0=1+t; x1=140-t
    for i,(L,R) in enumerate([((8,-80),(66,-28)),((4,-35),(42,-10)),((4,0),(40,0))]):
        dy,dz=R[0]-L[0],R[1]-L[1]; length=math.hypot(dy,dz)
        if i==2: length=q('wallGap')-4
        rot=App.Rotation(App.Vector(1,0,0),math.degrees(math.atan2(dz,dy)))
        sections.append(N.polygon([(x0,t),(x1,t),(x1,length-t),(x0,length-t)],(0,L[0],L[1]),rot,'duct section '+str(i+2)))
    return N.Solid.makeLoft(sections,ruled=True)

# Bind selected source literals at their exact source locations, not globally.
class Bindings(ast.NodeTransformer):
    def __init__(self,path): self.file=path.name
    def repl(self,expression,node): return ast.copy_location(ast.parse(expression,mode='eval').body,node)
    def visit_Constant(self,node):
        if not isinstance(node.value,(int,float)): return node
        v=node.value; line=node.lineno; expression=None
        if self.file=='build_mount.py':
            if line==37 and v==.3: expression="q('keyClearance')"
            # Rail Z layout: leave the keyed lower interface fixed.
            if 73<=line<=83:
                if v in [198,196,201]: expression="q('contractionStartZ')"+({198:'',196:'-2',201:'+3'}[v])
                if v in [226,227]: expression="q('throatZ')"+('' if v==226 else '+1')
                if v==232: expression="q('outletZ')"
                if v==188: expression="q('outletZ')-44"
                if v in [40,37.6,37,39]: expression="q('wallGap')"+({40:'',37.6:'-2.4',37:'-3',39:'-1'}[v])

        elif self.file=='base_geometry.py':
            if line in [59,77] and v==86: expression="q('wallGap')-2+q('bareSlot')+22"
            if line==150 and v in [1,5,9]: expression='fx('+str(v)+')'
            if line==148 and v==2.4: expression="q('grilleBarWidth')"
            if line==149 and v==71.4: expression="69+q('grilleBarWidth')"
            if line in [56,59,77] and v in [94,97]: expression="q('tineHeight')"+('' if v==94 else '+3')
            if line==56 and v==88: expression="q('tineHeight')-6"
            if line==76 and v==84: expression="q('tineHeight')-10"
        return self.repl(expression,node) if expression else node

# Additional coordinate bindings on box/prism calls preserve nominal wall-fixed material.
def box(x0,x1,y0,y1,z0,z1):
    if N.FAMILY in ['FanTray','FanCap']:
        x0,x1=fx(x0),fx(x1); z0,z1=sz(z0),sz(z1)
    if N.FAMILY=='FanDuct' and z0 in [-110,-107.6]: x0,x1=fx(x0),fx(x1)
    if N.FAMILY=='Cradle':
        def y(v):
            if v in [38,37,39,36]: return q('wallGap')+(v-40)
            if v in [61,64,66,68,78.6875,72.125,84,86,67,75.1875]: return q('wallGap')-2+q('bareSlot')+(v-64)
            return v
        y0,y1=y(y0),y(y1)
    return N.Workplane('XY').box(x1-x0,y1-y0,z1-z0).translate(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2))

def yz_prism(x0,x1,pts):
    if N.FAMILY in ['FanTray','FanCap']: x0,x1=fx(x0),fx(x1)
    if N.FAMILY=='Cradle':
        def y(v):
            if v in [64,84,75.1875,67,68,78.6875,72.125,65]: return q('wallGap')-2+q('bareSlot')+(v-64)
            if v==38: return q('wallGap')-2
            return v
        pts=[(y(a),b) for a,b in pts]
    if N.FAMILY in ['FanTray','FanCap']: pts=[(a,sz(b)) for a,b in pts]
    return N.Workplane('YZ',origin=(x0,0,0)).polyline(pts).close().extrude(x1-x0)
