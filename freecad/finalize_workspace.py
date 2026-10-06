from pathlib import Path
import importlib
import FreeCAD as A,FreeCADGui as G
import fusion_ribbon
importlib.reload(fusion_ribbon);fusion_ribbon.apply()
A.saveParameter()
A.Console.PrintMessage('Workspace saved. Geometry work complete; no recompute queued.\n')
