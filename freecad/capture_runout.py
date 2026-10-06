from pathlib import Path
import FreeCADGui as G
ROOT=Path(__file__).resolve().parent
v=G.activeDocument().mdiViewsOfType('Gui::View3DInventor')[0]
v.saveImage(str(ROOT/'boss_runout_live.png'),1400,1000,'Current')
