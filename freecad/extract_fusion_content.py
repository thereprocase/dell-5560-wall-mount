"""Inventory locally installed Fusion toolbar content, without copying artwork."""
from pathlib import Path
import json,re,xml.etree.ElementTree as E,hashlib
ROOT=Path(__file__).resolve().parent
INSTALL=max((Path.home()/"AppData/Local/Autodesk/webdeploy/production").iterdir(), key=lambda p:p.stat().st_mtime)
def parse(p):
 s=p.read_text(encoding="utf-8-sig")
 s=re.sub(r"<!DOCTYPE.*?\]>","",s,flags=re.S)
 s=re.sub(r"&(DebugPanels|LegacyPanels);","",s)
 return E.fromstring(s)
def node(e):
 return {"type":e.tag,**e.attrib,"children":[node(c) for c in e]}
files=[INSTALL/"Fusion/UI/FusionUI/Resources/Toolbar/TabToolbars.xml",INSTALL/"Applications/ParaMesh/UI/ParaMeshUI/Resources/Toolbar/TabToolbars.xml"]
result={"installation":str(INSTALL),"scope":"Installed definitions; runtime entitlement and user pin overrides may differ", "sources":[],"tabs":[],"panels":[],"command_labels":{},"icons":{}}
for p in files:
 tree=parse(p);result["sources"].append({"path":str(p),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
 result["tabs"].extend(node(e) for e in tree.iter("Tab"))
 result["panels"].extend(node(e) for e in tree.iter("Panel"))
for p in (INSTALL/"Fusion/UI").glob("*/Resources/CommandDefinitions/CommandDefinitions.xml"):
 try:tree=parse(p)
 except E.ParseError:continue
 for e in tree.iter("CommandDefinition"):
  text=e.find("./Tooltip/TextBlock")
  if text is not None and text.get("_LCLZText"):result["command_labels"][e.get("Id")]=text.get("_LCLZText")
res=INSTALL/"Fusion/UI/FusionUI/Resources"
for p in res.rglob("32x32-dark@2x.png"):result["icons"][str(p.parent.relative_to(res))]=str(p)
(ROOT/"fusion_installed_content.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
lines=["# Installed Fusion ribbon inventory","",result["scope"],"", "Artwork stays in the local Fusion installation; the inventory records paths only.",""]
for p in result["panels"]:
 if p.get("Id") not in ["SolidCreatePanel","SolidModifyPanel","AssemblePanel","ConfigurePanel","ConstructionPanel","InspectPanel","InsertPanel","SelectPanel"]:continue
 lines.extend(["## "+p.get("_LCLZText",p["Id"]),""])
 for section in p["children"]:
  lines.append(section["type"]+":")
  def walk(n,depth=0):
   id=n.get("Id","");name=result["command_labels"].get(id,n.get("_LCLZText",id or n["type"]))
   lines.append("  "*depth+"- "+name+(" (`"+id+"`)" if id else ""))
   for c in n["children"]:walk(c,depth+1)
  for n in section["children"]:walk(n)
  lines.append("")
(ROOT/"FUSION_INSTALLED_CONTENT.md").write_text("\n".join(lines),encoding="utf-8")
print(json.dumps({k:len(result[k]) for k in ["tabs","panels","command_labels","icons"]}))
