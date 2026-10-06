"""Organize the existing Parameters object without changing its identity or aliases."""
from pathlib import Path
import json,sys
import FreeCAD as App,FreeCADGui as Gui
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import native_ops as N,design_bindings as B
D=App.ActiveDocument; N.D=D; P=D.getObject('Parameters')
B.setup(P)
values={P.getAlias(c):P.getContents(c) for c in P.getNonEmptyCells() if P.getAlias(c)}
(ROOT/'parameters_before_layout.json').write_text(json.dumps(values,indent=2))
expressions=[(o.Name,list(o.ExpressionEngine)) for o in D.Objects if o.ExpressionEngine]
meta={name:(unit,category,role) for name,_,unit,category,role in B.SPECS}
for name in values:
    if name not in meta: meta[name]=('mm','Push pin' if name.startswith('pin') else 'Outlet',{'outletGap':'Both outlet rails; nominal configuration 12 mm'}.get(name,'Shared pin geometry / mating fit'))
groups=['Layout','Structure','Wall mounting','Fan module','Duct','Outlet','Fits','Push pin','Service']
P.clearAll()
P.mergeCells('A1:F1'); P.set('A1','PRECISION 5560 | REVISION F | DESIGN INPUTS')
P.setBackground('A1:F1',(0.08,0.16,0.23)); P.setForeground('A1:F1',(1,1,1)); P.setStyle('A1:F1','bold','add'); P.setRowHeight('1',32)
P.mergeCells('A2:F2'); P.set('A2','Blue values = editable inputs   |   Gray values = derived formulas   |   Native feature dimensions remain editable in sketches')
P.setRowHeight('2',26)
for c,t in zip('ABCDEF',['Parameter','Value','Unit','Controls','Validation','Kind']): P.set(c+'4',t)
P.setStyle('A4:F4','bold','add'); P.setBackground('A4:F4',(.82,.87,.9))
row=6; index={}
for group in groups:
    names=[n for n in values if meta[n][1]==group]
    if not names: continue
    P.mergeCells('A'+str(row)+':F'+str(row)); P.set('A'+str(row),group.upper())
    P.setBackground('A'+str(row)+':F'+str(row),(.16,.29,.37)); P.setForeground('A'+str(row)+':F'+str(row),(1,1,1)); P.setStyle('A'+str(row)+':F'+str(row),'bold','add'); P.setRowHeight(str(row),26); row+=1
    for name in names:
        unit,_,role=meta[name]; r=str(row); cell='B'+r
        P.set('A'+r,name); P.set(cell,values[name]); P.setAlias(cell,name); P.set('C'+r,unit); P.set('D'+r,role)
        derived=name in B.FORMULAS
        P.set('F'+r,'Derived' if derived else 'Input')
        P.setBackground(cell,(.9,.91,.92) if derived else (.79,.9,.98))
        P.setForeground(cell,(.16,.19,.22) if derived else (.03,.22,.42))
        P.set('E'+r,'Nominal / perturbation checks pending')
        P.setRowHeight(r,24); index[name]=cell; row+=1
    row+=1
for o,engine in expressions:
    obj=D.getObject(o)
    if obj:
        for prop,expression in engine: obj.setExpression(prop,expression)
for c,width in [('A',230),('B',130),('C',55),('D',540),('E',280),('F',75)]: P.setColumnWidth(c,width)
D.recompute()
(ROOT/'parameter_cells.json').write_text(json.dumps(index,indent=2))
Gui.activeDocument().setEdit(P.Name); Gui.updateGui()
