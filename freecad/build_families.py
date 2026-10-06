"""Build the five native part families from the preserved Revision F recipes."""
from pathlib import Path
import ast, types, sys, math, json, time, traceback
import FreeCAD as App, Part
import FreeCADGui as Gui
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import native_ops as N
import importlib
importlib.reload(N)
D=App.ActiveDocument
if D is None or D.getObject('PinBody') is None: raise RuntimeError('Open the pin checkpoint first')
N.D=D
import design_bindings as B
importlib.reload(B)
if not D.getObject('Parameters').getCellFromAlias('fanFrameWidth'): B.setup(D.getObject('Parameters'))
P=D.getObject('Parameters')
class Names(ast.NodeTransformer):
    def visit_Assign(self,node):
        self.generic_visit(node)
        if len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and isinstance(node.value,ast.Call):
            name=node.targets[0].id
            if name not in ('pts','levels','lev','items','guard','lands','bosses','spokes'):
                node.value=ast.Call(func=ast.Name(id='tag',ctx=ast.Load()),args=[node.value,ast.Constant(name)],keywords=[])
        return node

def load(path,functions,extra=None):
    tree=ast.parse(path.read_text())
    selected=[]
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name in functions: selected.append(node)
        elif isinstance(node,ast.Assign) and all(isinstance(t,ast.Name) and t.id not in ('OUT','PARTS') for t in node.targets): selected.append(node)
    tree=Names().visit(B.Bindings(path).visit(ast.Module(body=selected,type_ignores=[]))); ast.fix_missing_locations(tree)
    ns={'cq':N,'math':math,'tag':N.tag,'q':B.q,'fx':B.fx}
    if extra: ns.update(extra)
    exec(compile(tree,str(path),'exec'),ns)
    return ns
base=load(ROOT.parent/'base_geometry.py',{'box','cyl','yz_prism','fuse','roof_hole','tongue','right_cradle','right_tray','right_cap','laptop_reference','fan_reference'})
base.update({k:getattr(B,k) for k in ['box','cyl','yz_prism','roof_hole','tongue']})
# Functions retain their dictionary globals, so these updates bind all nested calls.
old=types.SimpleNamespace(**base)
revision=load(ROOT.parent/'build_mount.py',{'tilt','untilt','tenons','right_cradle','wire','loft_channel','right_duct','right_tray','right_cap','right_rail'},
              {'old':old,**{k:base[k] for k in ('box','cyl','yz_prism','fuse','roof_hole','tongue')}})

revision.update({'tilt':B.tilt,'loft_channel':B.loft_channel})

families=[('Cradle','right_cradle','02_right_cradle','01_left_cradle'),
          ('FanDuct','right_duct','04_right_fan_duct','03_left_fan_duct'),
          ('FanCap','right_cap','06_right_fan_retainer','05_left_fan_retainer'),
          ('OutletRail','right_rail','08_right_outlet_rail','07_left_outlet_rail'),
          ('FanTray','right_tray','10_right_fan_tray','09_left_fan_tray')]
report=json.loads((ROOT/'native_validation.json').read_text()) if (ROOT/'native_validation.json').exists() else {}
for family,fn,rightname,leftname in families:
    if D.getObject(family+'History'):
        keys={getattr(o,'PartKey','') for o in D.getObject(family+'History').Group}
        if rightname in keys and leftname in keys: continue
        raise RuntimeError('Incomplete '+family+' history: inspect before resuming')
    N.FAMILY=family; N.GROUP=D.addObject('App::DocumentObjectGroup',family+'History'); N.GROUP.Label=family+' — native construction'
    D.openTransaction('Build '+family)
    try:
        App.Console.PrintMessage('Building '+family+'\n'); Gui.updateGui()
        result=revision[fn](N.Expr(12,'(Parameters.outletGap / (1 mm))')) if family=='OutletRail' else revision[fn]()
        result=N.unwrap(result).translate((B.dx(),0,0))
        wrapper=N.new('Part::Compound','module coordinates'); wrapper.Links=[result.obj]
        result=N.update(wrapper,[result.obj]); result.obj.Label=rightname
        result.obj.addProperty('App::PropertyString','PartKey','Identity'); result.obj.PartKey=rightname
        mirrored=result.mirror('YZ'); mirrored.obj.Label=leftname
        mirrored.obj.addProperty('App::PropertyString','PartKey','Identity'); mirrored.obj.PartKey=leftname
        for o in N.GROUP.Group: o.Visibility=False
        result.obj.Visibility=True; mirrored.obj.Visibility=True
        for key,obj in [(rightname,result.obj),(leftname,mirrored.obj)]:
            shape=obj.Shape
            baseline=Part.read(str(ROOT.parent/'parts'/(key+'.step')))
            a=shape.cut(baseline); b=baseline.cut(shape)
            report[key]={'object':obj.Name,'valid':shape.isValid(),'solids':len(shape.Solids),
                         'volume_mm3':shape.Volume,'baseline_volume_mm3':baseline.Volume,
                         'symmetric_difference_mm3':a.Volume+b.Volume,
                         'bbox':[getattr(shape.BoundBox,k) for k in ['XMin','XMax','YMin','YMax','ZMin','ZMax']]}
            if not shape.isValid() or len(shape.Solids)!=1: raise RuntimeError('Invalid final '+key)
        D.commitTransaction()
        D.recompute(); D.save()
        (ROOT/'native_validation.json').write_text(json.dumps(report,indent=2))
        Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0].viewAxonometric(); Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0].fitAll(); Gui.updateGui()
        Gui.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0].saveImage(str(ROOT/(family+'_preview.png')),1400,1000,'Current')
    except Exception:
        D.commitTransaction()
        D.saveAs(str(ROOT/'Precision_5560_Build_Recovery.FCStd'))
        (ROOT/'build_failure.txt').write_text(traceback.format_exc())
        raise
(ROOT/'build_progress.json').write_text(json.dumps({'status':'families complete','features':N.COUNT},indent=2))

# Rounded planar sketches avoid fragile edge links during dimensional edits.
import rounded_profiles
rounded_profiles.replace(D)
D.recompute(); D.save()
