from pathlib import Path
import sys, json, math
import FreeCAD as App, Part
import FreeCADGui as Gui
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(Path(App.getResourceDir())/'Mod'/'Assembly'))
import JointObject
D=App.ActiveDocument
sources={o.PartKey:o for o in D.Objects if 'PartKey' in o.PropertiesList}
if len(sources)!=10: raise RuntimeError('Expected ten completed handed source parts')
if D.getObject('InstalledAssembly'): raise RuntimeError('Assembly already exists')
assembly=D.addObject('Assembly::AssemblyObject','InstalledAssembly'); assembly.Label='Installed assembly — 14 printed parts'; assembly.Type='Assembly'
joints=assembly.newObject('Assembly::JointGroup','Joints')
links={}
for key,source in sources.items():
    link=assembly.newObject('App::Link','Instance'); link.setLink(source); link.LinkPlacement=source.Placement
    link.Label=key.replace('_',' ')+' (installed)'; link.addProperty('App::PropertyString','InstanceKey','Identity'); link.InstanceKey=key; links[key]=link
    source.Visibility=False
    source.ViewObject.ShapeColor=(.13,.52,.57) if any(k in key for k in ('duct','rail')) else (.34,.39,.44)
    link.Visibility=True
pin=D.getObject('PinBody')
P=D.getObject('Parameters')
rot=App.Rotation(App.Vector(1,0,0),45)
for index,x in [(11,-5),(12,5),(13,-135),(14,135)]:
    side='left' if x<0 else 'right'; key=f'{index:02}_{side}_push_pin'
    link=assembly.newObject('App::Link','PinInstance'); link.setLink(pin)
    pos=App.Vector(0,67,-84)+rot.multVec(App.Vector(x,76,1))
    link.LinkPlacement=App.Placement(pos,App.Rotation(App.Vector(1,0,0),135))
    sign=1 if x>0 else -1
    edge_sign=-1 if abs(x)==5 else 1
    xexpr=f'{sign} * ({abs(x)} mm + {edge_sign} * (Parameters.fanFrameWidth - 120 mm)/2 + (Parameters.laptopWidth - 344.4 mm)/2)'
    link.setExpression('LinkPlacement.Base.x',xexpr)
    link.setExpression('LinkPlacement.Base.y','Parameters.fanCenterY + 76 mm*cos(Parameters.fanAngle) - 1 mm*sin(Parameters.fanAngle)')
    link.setExpression('LinkPlacement.Base.z','Parameters.fanCenterZ + 76 mm*sin(Parameters.fanAngle) + 1 mm*cos(Parameters.fanAngle)')
    link.setExpression('LinkPlacement.Rotation.Angle','Parameters.fanAngle + 90 deg')
    link.Label=key.replace('_',' ')+' (installed)'; link.addProperty('App::PropertyString','InstanceKey','Identity'); link.InstanceKey=key; links[key]=link; pin.ViewObject.ShapeColor=(.88,.65,.22)
pin.Visibility=False
D.recompute()
for side in ['left','right']:
    def find(word): return next(o for key,o in links.items() if side in key and word in key)
    cradle=find('cradle'); duct=find('fan_duct'); rail=find('outlet_rail'); cap=find('fan_retainer'); tray=find('fan_tray')
    g=joints.newObject('App::FeaturePython','GroundedCradle'); g.Label=side+' cradle — grounded to wall layout'
    JointObject.GroundedJoint(g,cradle); JointObject.ViewProviderGroundedJoint(g.ViewObject)
    pairs=[(cradle,duct,0,'duct saddle'),(cradle,rail,0,'rail keys'),(duct,cap,0,'cap installed'),(duct,tray,3,'tray service slider')]
    pairs += [(cap,o,0,'push pin installed') for key,o in links.items() if side in key and 'push_pin' in key]
    for first,second,type_index,label in pairs:
        j=joints.newObject('App::FeaturePython','Joint'); j.Label=side+' — '+label
        JointObject.Joint(j,type_index); JointObject.ViewProviderJoint(j.ViewObject)
        j.Detach1=True; j.Detach2=True
        j.Reference1=(first,['']); j.Reference2=(second,[''])
        orient=App.Rotation(App.Vector(0,0,1),App.Vector(0,2**-.5,2**-.5)) if type_index==3 else App.Rotation()
        world=App.Placement(App.Vector(0,67,-84),orient)
        j.Placement1=first.Placement.inverse().multiply(world)
        j.Placement2=second.Placement.inverse().multiply(world)
        if 'push pin' in label:
            j.Placement1=second.LinkPlacement
            j.Placement2=App.Placement()
            for prop,expression in second.ExpressionEngine:
                if prop.startswith('LinkPlacement.'):
                    j.setExpression(prop.replace('LinkPlacement.','Placement1.'),expression)
        if type_index==3:
            j.setExpression('Placement1.Rotation.Angle','90 deg - Parameters.fanAngle')
            j.setExpression('Placement2.Rotation.Angle','90 deg - Parameters.fanAngle')
        j.Visibility=False
D.recompute()
before={k:o.Placement for k,o in links.items()}
solve_result=assembly.solve()
D.recompute()
report={'instances':len(links),'distinct_part_sources':11,'solve_result':str(solve_result),
        'joint_types':{j.Name:getattr(j,'JointType','Grounded') for j in joints.Group},'parts':{},
        'solver_translation_delta_mm':{k:(o.Placement.Base-before[k].Base).Length for k,o in links.items()}}
for key,o in links.items():
    shape=o.Shape
    baseline=Part.read(str(ROOT.parent/'parts'/(key+'.step')))
    diff=shape.cut(baseline).Volume+baseline.cut(shape).Volume
    report['parts'][key]={'valid':shape.isValid(),'solids':len(shape.Solids),'volume_mm3':shape.Volume,'symmetric_difference_mm3':diff}
(ROOT/'assembly_native_validation.json').write_text(json.dumps(report,indent=2))
P=D.getObject('Parameters')
layout=D.getObject('Layout') or D.addObject('App::DocumentObjectGroup','Layout'); layout.Label='Layout and reference envelopes'
lap=D.getObject('LaptopEnvelope') or D.addObject('Part::Box','LaptopEnvelope'); layout.addObject(lap); lap.Label='REFERENCE — conservative laptop fit envelope'
for prop,expression in [('Length','Parameters.laptopWidth'),('Width','Parameters.laptopThickness'),('Height','Parameters.laptopHeight'),('Placement.Base.x','-Parameters.laptopWidth/2'),('Placement.Base.y','Parameters.wallGap')]: lap.setExpression(prop,expression)
lap.Placement.Base.z=2
lap.ViewObject.Transparency=85; lap.Visibility=False
for o in D.Objects:
    if o.TypeId=='Sketcher::SketchObject': o.Visibility=False
for n in ['CradleHistory','FanDuctHistory','FanCapHistory','OutletRailHistory','FanTrayHistory']:
    D.getObject(n).Visibility=False
D.recompute(); D.saveAs(str(ROOT/'Precision_5560_Native.FCStd'))
__import__('Import').export(list(links.values()),str(ROOT/'Precision_5560_Native.step'))
Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0].viewAxonometric(); Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0].fitAll(); Gui.updateGui()
Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0].saveImage(str(ROOT/'assembly_preview.png'),1600,1200,'Current')
