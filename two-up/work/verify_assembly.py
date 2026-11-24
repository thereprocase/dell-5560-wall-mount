import FreeCAD as App
doc = App.openDocument('two-up/work/Laptop_Wall_Mount_TwoUp.FCStd')
for key in ['01_left_lower_arm','02_right_lower_arm','09_left_upper_arm','10_right_upper_arm','03_left_fan_cage','13_left_tier1_cheek_panel','15_left_tier2_cheek_panel']:
    o = doc.getObject('TwoUpInstalled' + key.replace('_',''))
    bb = o.Shape.BoundBox
    print(f"{key:<26} link_base={o.LinkPlacement.Base} src={o.LinkedObject.Placement.Base} bboxX=({bb.XMin:7.1f},{bb.XMax:7.1f}) bboxZ=({bb.ZMin:7.1f},{bb.ZMax:7.1f})")
