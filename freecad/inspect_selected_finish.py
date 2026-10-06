from pathlib import Path
import json
import FreeCAD as A,FreeCADGui as G
ROOT=Path(__file__).resolve().parent
out=[]
for s in G.Selection.getSelectionEx():
 item={'document':s.DocumentName,'object':s.ObjectName,'label':s.Object.Label,'subelements':list(s.SubElementNames),'points':[[p.x,p.y,p.z] for p in s.PickedPoints],'faces':[]}
 for name in s.SubElementNames:
  f=s.Object.getSubObject(name)
  item['faces'].append({'name':name,'area':f.Area,'vertices':[[v.Point.x,v.Point.y,v.Point.z] for v in f.Vertexes],'surface':str(getattr(f,'Surface',''))})
 out.append(item)
(ROOT/'selected_finish.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
