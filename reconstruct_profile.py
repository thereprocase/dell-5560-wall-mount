"""Scale manufacturer images, record explicit picks and reconstruct an approximate section."""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw
import cadquery as cq
from render_preview import font
from build_mount import yz_prism,OUT

def main():
 ref=OUT/'reference';side=Image.open(ref/'Dell_5560_Right.jpg');inside=Image.open(ref/'Dell_5560_Base_Inside.jpg')
 sx=230.3/(1722-79)
 picks=[(79,171),(1697,156),(1722,240),(1690,260),(1650,280),(1630,292),(1614,291),(1594,281),(400,281),(347,292),(334,288),(213,276),(150,251),(98,222)]
 profile=[(40+(280-y)*sx,2+(x-79)*sx) for x,y in picks]
 # Internal-cover image separately scaled in each axis; perspective/illustration limits retained.
 ix=344.4/(1476-80);iz=230.3/(974-48)
 windows=[dict(x_mm=[(x0-80)*ix-172.2,(x1-80)*ix-172.2],z_mm=[2+(974-375)*iz,2+(974-213)*iz]) for x0,x1 in [(186,470),(1087,1371)]]
 data={'revision':'F','method':'Manual pixel picks scaled to published 230.3-mm depth and 344.4-mm width. Approximate external silhouette, not a manufacturer cross-section.','side_image_bounds_x_px':[79,1722],'side_mm_per_pixel':sx,'side_outline_pixels':picks,'profile_yz_mm':profile,'profile_estimated_uncertainty_mm':2,'internal_case_bounds_pixels':[80,48,1476,974],'internal_scale_x_mm_px':ix,'internal_scale_z_mm_px':iz,'effective_intake_windows':windows,'intake_location_uncertainty_mm':4,'CFD_foot_projection_mm':2,'CFD_foot_projection_uncertainty_mm':1,'published_height_caution':'Dell lists 7.70/11.65 mm; side-image closed silhouette is thicker. Do not treat those entries as verified closed assembly thickness. Keep 20-mm fit envelope.','source_urls':{'side':'https://dl.dell.com/content/guides/public/html//prec5560_ss/images/GUID-C9E741CA-573F-4F5F-85BB-CD9ECC09733B-low.jpg','inside':'https://dl.dell.com/content/guides/public/Html/prec5560_sm/images/GUID-D9E7DDF5-01D6-4E98-B3FB-83A574C6A4BE-low.jpg'},'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ref/'Dell_5560_Right.jpg',ref/'Dell_5560_Left.jpg',ref/'Dell_5560_Base_Inside.jpg']}}
 (OUT/'profile_reconstruction.json').write_text(json.dumps(data,indent=2))
 s=yz_prism(-172.2,172.2,profile).val();assert s.isValid()
 cq.exporters.export(s,str(OUT/'REFERENCE_Estimated_Laptop_Profile.step'))
 # Scaled reference image: 5 pixels per mm across depth, no invented aspect-ratio correction.
 crop=side.crop((79,145,1722,302));crop=crop.resize((round(230.3*5),round(crop.height*sx*5)))
 crop.save(ref/'Right_Profile_5px_per_mm.png')
 im=Image.new('RGB',(1800,1450),'#f8f8f8');d=ImageDraw.Draw(im)
 d.text((55,35),'LAPTOP GEOMETRY FROM DELL REFERENCES',font=font(37,True),fill='#172838')
 d.text((55,95),'Scaled imagery + inferred section | Keep the 20 mm fit envelope until measured.',font=font(24),fill='#526472')
 view=side.copy();dv=ImageDraw.Draw(view);dv.line(picks+[picks[0]],fill='#e58d23',width=3)
 im.paste(view.resize((1680,413)),(60,160));d=ImageDraw.Draw(im)
 d.text((60,560),'230.3 mm depth | Image-derived silhouette: roughly 18–20 mm including lid/feet; ±2 mm estimate.',font=font(22),fill='#526472')
 inner=inside.copy();di=ImageDraw.Draw(inner)
 for x0,x1 in [(186,470),(1087,1371)]:di.rectangle((x0,213,x1,375),outline='#168887',width=6)
 im.paste(inner.resize((1000,620)),(60,640));d=ImageDraw.Draw(im)
 d.text((1110,685),'TWO ACTIVE INTAKE REGIONS',font=font(23,True),fill='#168887')
 for j,line in enumerate(['Approx. 70 × 40 mm each','Centers approx. X = ±111 mm','Height approx. Z = 151–191 mm','Conservative uncertainty: ±4 mm','','The internal cover masks the center.','External grille width overstates','the open intake area.','','Cross-section is reconstructed.','No dimensioned factory section found.']):d.text((1110,740+j*37),line,font=font(23),fill='#172838')
 d.text((60,1330),'Source: Dell Precision 5560 Setup/Specifications and Service Manual. Pixel picks and original images included.',font=font(22),fill='#526472')
 d.text((60,1370),'The CFD uses a representative intake-band section and a 2 mm rear-foot projection; neither is a measured unit.',font=font(22),fill='#526472')
 im.save(OUT/'Laptop_Profile_References.png')
 print(json.dumps(data,indent=2))
if __name__=='__main__':main()
