from pathlib import Path
import json
import FreeCADGui as G
r={'workbenches':list(G.listWorkbenches()),'commands':G.listCommands()}
Path(__file__).with_name('command_inventory.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
