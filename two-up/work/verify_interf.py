import FreeCAD as App
doc = App.openDocument('two-up/work/Laptop_Wall_Mount_TwoUp.FCStd')
def sh(k): return doc.getObject('TwoUpInstalled'+k.replace('_','')).Shape
pairs=[('13_left_tier1_cheek_panel','01_left_lower_arm'),
       ('15_left_tier2_cheek_panel','09_left_upper_arm'),
       ('07_left_tier1_splitter_dam','01_left_lower_arm'),
       ('11_left_tier2_dam','09_left_upper_arm'),
       ('17_left_arm_splice_key','01_left_lower_arm'),
       ('17_left_arm_splice_key','09_left_upper_arm'),
       ('03_left_fan_cage','01_left_lower_arm')]
for a,b in pairs:
    inter = sh(a).common(sh(b))
    print(f"{a:<28} vs {b:<22} interference={inter.Volume:10.2f} mm3")
