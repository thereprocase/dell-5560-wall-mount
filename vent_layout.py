"""Current vent alignment diagram using scaled Dell references and CAD coordinates."""
import json
from PIL import Image,ImageDraw
from build_mount import OUT
from render_preview import font

def main():
 dta=json.loads((OUT/'profile_reconstruction.json').read_text())
 data={'revision':'F','effective_intake_windows':dta['effective_intake_windows'],'intake_location_uncertainty_mm':4,'contraction_start_z_mm':198,'throat_z_mm':226,'exit_z_mm':232,'hinge_z_mm':232.3,'slot_gaps_mm':[8,12,16],'nominal_gap_mm':12,'foot_projection_estimate_mm':2,'method':'Scaled manufacturer imagery; CFD representative section. See profile_reconstruction.json.'}
 (OUT/'vent_layout_measurements.json').write_text(json.dumps(data,indent=2))
 page=Image.new('RGB',(1600,1300),'#f8f8f8');d=ImageDraw.Draw(page)
 d.text((55,35),'INTAKE / CONTRACTION / OUTLET',font=font(38,True),fill='#172838')
 d.text((55,100),'Revision F | Geometry alignment, not a thermal or room-plume prediction',font=font(23),fill='#526472')
 # Coordinate diagram at true equal scale in the YZ plane.
 def p(y,z):return (140+y*5,1335-z*5)
 d.rectangle([p(-4,234),p(0,140)],fill='#ccd2d8')
 d.rectangle([p(40,232.3),p(60,145)],fill='#ccd2d8',outline='#526472',width=2)
 d.rectangle([p(38,222),p(40,216)],fill='#526472')
 d.line([p(40,151),p(40,191)],fill='#dc621c',width=8)
 pts=[(0,196),(4,198),(28,226),(28,232),(25.6,232),(25.6,227),(0,201)]
 d.polygon([p(*v) for v in pts],fill='#168887')
 for z,txt,col in [(191,'Estimated intake top ≈191 mm','#dc621c'),(198,'Contraction begins at198 mm','#168887'),(226,'12 mm throat at226 mm','#168887'),(232,'Exit at232 mm / hinge at232.3 mm','#172838')]:
  y=p(0,z)[1];d.line((500,y,740,y),fill=col,width=2)
  yy={191:730,198:585,226:340,232:230}[z]
  d.line((740,y,810,yy+15),fill=col,width=2);d.text((825,yy),txt.replace('at1','at 1').replace('at2','at 2'),font=font(25,True),fill=col)
 d.text((820,830),'Two open regions near the blowers:',font=font(26,True),fill='#172838')
 for i,t in enumerate(['Approx. 70 × 40 mm each','Centers near X=±111 mm','Height band ≈151–191 mm, uncertainty ±4 mm','Rear-foot projection: 2 mm assumed, unmeasured','Cheek lips stop behind the side ports.']):d.text((820,885+i*43),t,font=font(23),fill='#526472')
 d.text((55,1160),'The contraction starts above the estimated intake. Its maximum slope is 45° for the 8 mm rail.',font=font(24),fill='#172838')
 d.text((55,1210),'Nominal gap refers to the underside plane; feet, print tolerances and leakage require a physical check.',font=font(23),fill='#526472')
 page.save(OUT/'Vent_Layout_and_Outlet.png')
if __name__=='__main__':main()
