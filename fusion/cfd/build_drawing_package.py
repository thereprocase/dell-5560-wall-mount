"""Lay out the CFD engineering review set; render every page for QA."""
from pathlib import Path
import sys, json, hashlib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tmp/pdfdeps'))
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
import fitz

OUT=ROOT/'output/pdf'; ASSETS=OUT/'assets_release'; OUT.mkdir(parents=True,exist_ok=True)
PATH=OUT/'Precision_5560_CFD_Technical_Review.pdf'
W,H=landscape(A3)
INK='#163747'; TEAL='#087F91'; GRAY='#526975'; PALE='#EDF3F5'; AMBER='#A46317'
c=canvas.Canvas(str(PATH),pagesize=(W,H),pageCompression=1)
c.setTitle('Precision 5560 | Installed Airflow | Technical Review Set')
c.setAuthor('Dell 5560 wall-mount project')
c.setSubject('Iteration 1200 CFD visualization - exploratory, not converged')

def txt(x,y,s,size=11,color=INK,bold=False):
    c.setFillColor(HexColor(color));c.setFont('Helvetica-Bold' if bold else 'Helvetica',size);c.drawString(x,H-y,s)
def line(x1,y1,x2,y2,col='#CAD7DC',width=.6):
    c.setStrokeColor(HexColor(col));c.setLineWidth(width);c.line(x1,H-y1,x2,H-y2)
def rect(x,y,w,h,fill=None,stroke='#CAD7DC'):
    if fill:c.setFillColor(HexColor(fill))
    c.setStrokeColor(HexColor(stroke));c.setLineWidth(.6);c.rect(x,H-y-h,w,h,stroke=1,fill=int(fill is not None))
def para(x,y,w,s,size=11,color=GRAY):
    p=Paragraph(s,ParagraphStyle('body',fontName='Helvetica',fontSize=size,leading=size*1.45,textColor=HexColor(color)))
    _,h=p.wrap(w,1000);p.drawOn(c,x,H-y-h);return h
def img(name,x,y,w,h):
    r=ImageReader(str(ASSETS/f'{name}.png'));iw,ih=r.getSize();scale=min(w/iw,h/ih);dw,dh=iw*scale,ih*scale
    c.drawImage(r,x+(w-dw)/2,H-y-(h+dh)/2,width=dw,height=dh,mask='auto')
def label(n,title,x,y):
    txt(x,y,n,10,TEAL,True);txt(x+32,y,title,12,INK,True)
def page(n,title,subtitle):
    c.bookmarkPage(f'sheet{n}');c.addOutlineEntry(f'{n:02d}  {title}',f'sheet{n}',0)
    rect(23,23,W-46,H-46)
    txt(38,47,'PRECISION 5560 / WALL-MOUNT COOLING',10,TEAL,True)
    txt(38,82,title,27,INK,True)
    txt(38,104,subtitle,10,GRAY)
    txt(W-267,46,'SIMULATION TECHNICAL REVIEW',10,INK,True)
    txt(W-267,65,'REV A  |  07 SEP 2026  |  A3 LANDSCAPE',9,GRAY)
    line(38,117,W-38,117,TEAL,1.2)
    line(23,H-68,W-23,H-68)
    txt(38,H-46,'D5560-CFD-001',11,INK,True)
    txt(38,H-30,'CASE: installed_pressure10_v3',8,GRAY)
    txt(294,H-46,'EXPLORATORY / NOT CONVERGED',10,AMBER,True)
    txt(294,H-30,'Airflow only. Assumed fan forcing. Not a manufacturing release.',8,GRAY)
    txt(770,H-46,'UNITS: mm, m/s, Pa   |   VIEWS: NTS',9,INK)
    txt(770,H-30,'Saved solution: iteration 1200   |   836,278 cells',8,GRAY)
    txt(W-122,H-43,f'{n:02d} / 07',16,INK,True)
def finish():c.showPage()
def heading(x,y,t):txt(x,y,t,12,TEAL,True)
def metric(x,y,value,desc):txt(x,y,value,28,INK,True);txt(x,y+21,desc,10,GRAY)
def speedbar(x,y,w):
    # Same turbo lookup as the VTK and section assets, sampled from image LUT.
    colors=['#30123b','#4662d7','#35aaf8','#1be5b5','#72fe5e','#c8ee34','#faba39','#f66b19','#ca2a04','#7a0403']
    for i,col in enumerate(colors):rect(x+w*i/10,y,w/10,8,col,col)
    txt(x,y+23,'0',8,GRAY);txt(x+w-5,y+23,'5',8,GRAY);txt(x+w/2-31,y+23,'Speed [m/s]',8,GRAY)

page(1,'Installed airflow / system overview','Parallel-projection flow views | Actual reconstructed solution | Four idealized fan actuators')
img('isometric_flow',38,130,760,588)
speedbar(225,726,320)
line(817,135,817,748)
heading(844,153,'01  /  MODEL SCOPE')
para(844,172,285,'Native mount assembly, traced laptop envelope, twin intake windows, internal surrogate ducts and two external fan housings.',12)
heading(844,268,'02  /  OPERATING ASSUMPTION')
para(844,286,285,'Four constant-force actuators, each based on nominal 10 Pa pressure rise. No manufacturer fan curve or measured grille / fin resistance.',12)
metric(844,421,'3.52 / 3.55','Left / right sampled intake flow [CFM]')
metric(844,503,'4.93','Maximum cell speed [m/s]')
heading(844,575,'03  /  REVIEW STATUS')
para(844,593,285,'The run reached its 1200-iteration limit. Integral intake flows changed less than 0.7% from iteration 400; residual convergence was not achieved.',12)
para(844,691,285,'Streamlines show selected seeded paths, not total airflow allocation. Paths are clipped by the view frame.',9)
finish()

page(2,'Geometry / orthographic reference','Independent parallel views | Viewing directions stated explicitly | No implied first- or third-angle layout')
for n,title,name,x,y,w,h in [('A','VIEW FROM +Y / LOOKING -Y','front',38,136,536,270),('B','VIEW FROM +X / LOOKING -X','side',614,136,536,270),('C','VIEW FROM +Z / LOOKING -Z','top',38,438,536,270),('D','ISOMETRIC / SOLID ENVELOPE','iso_solid',614,438,536,270)]:
    label(n,title,x,y);img(name,x,y+9,w,h);line(x,y+h+16,x+w,y+h+16)
para(38,747,1100,'X = laptop width; Y = distance from wall; Z = installed height. Wall face Y = 0. Traced shell width 344.4 mm. Opaque views show the exterior envelope; hidden internal ducts are resolved on sheets 03-05.',9)
finish()

page(3,'Longitudinal sections / fan-to-laptop path','A-A: X = -111.017 mm   |   B-B: X = +111.264 mm   |   Scalar: speed   |   Equal axis scaling')
label('A-A','LEFT FAN / DUCT CENTRE',38,141);img('section_left',38,153,385,566)
label('B-B','RIGHT FAN / DUCT CENTRE',435,141);img('section_right',435,153,385,566)
heading(855,152,'SECTION REGISTER')
# Dimensioned X-Z locator: schematic, explicitly labeled, not geometry claim.
rect(877,201,220,147,None,INK)
for xpos,letter in [(916,'A'),(1058,'B')]:
    c.setDash(5,3);line(xpos,184,xpos,367,TEAL,1);c.setDash()
    txt(xpos-4,179,letter,12,TEAL,True);txt(xpos-4,383,letter,12,TEAL,True)
line(877,403,1097,403,INK);line(877,395,877,409,INK);line(1097,395,1097,409,INK)
txt(944,420,'344.4 mm',11,INK,True)
txt(876,445,'X-Z locator / schematic, +X to right',9,GRAY)
heading(855,486,'READING THE SECTIONS')
para(855,504,276,'The external fans sit below the laptop. The narrow cavity within the shell connects the active intake window to the hinge outlet. White areas indicate solid geometry or invalid samples.',11)
heading(855,618,'GEOMETRY CONFIDENCE')
para(855,636,276,'Envelope traced from the project reference: approximately +/-2 mm. Intake locations: approximately +/-4 mm. Internal ducts and fan placement are engineering surrogates.',10)
para(38,747,780,'Dark lines: intersection of CAD-derived surfaces with the section plane. Color field: interpolated velocity on cut cells; 0-5 m/s on all speed sheets.',9)
finish()

page(4,'Internal duct plane / velocity and pressure','C-C: Y = 45.000 mm   |   Plane passes through both simulated internal fan regions')
label('01','SPEED MAGNITUDE',38,142);img('duct_plane',38,150,735,269)
label('02','GAUGE PRESSURE',38,447);img('pressure_plane',38,455,735,269)
heading(823,161,'PLANE LOCATION')
para(823,181,305,'Y is measured outward from the wall. The assumed duct spans Y = 41.2 to 49.2 mm; this section lies inside its 8 mm depth.',12)
heading(823,303,'PRESSURE CONVENTION')
para(823,323,305,'OpenFOAM stores kinematic pressure. The plotted gauge pressure is p multiplied by rho = 1.2 kg/m3, referenced to the zero-pressure ambient boundary.',12)
heading(823,459,'INTERPRETATION')
para(823,479,305,'The two isolated colored passages are the modeled internal ducts. The white central region is solid laptop surrogate. The color maps are not temperature fields.',12)
heading(823,613,'DISPLAY LIMITS')
para(823,633,305,'Speed: 0 to 5 m/s. Pressure: -12 to +12 Pa, with saturation outside this range. Cells VTK cannot contour are omitted; gaps are not filled.',11)
finish()

page(5,'Transverse intake section / reverse perspective','D-D: Z = 171.119 mm   |   Intake-centre section with rear-side streamline context')
label('D-D','HORIZONTAL SECTION THROUGH ACTIVE INTAKES',38,142);img('intake_cross',38,151,1100,238)
line(38,411,W-38,411)
label('01','REVERSE OBLIQUE / FLOW CONTEXT',38,437);img('reverse_iso',38,449,615,298)
heading(714,457,'FLOW SAMPLES AT THE INTAKES')
para(714,477,409,'Rectangle quadrature at Y = 40.5 mm, with positive flow into the laptop. All quadrature points were valid at both intakes.',11)
rows=[('Location','Iteration 400','Iteration 1200'),('Left intake','3.498 CFM','3.520 CFM'),('Right intake','3.522 CFM','3.546 CFM')]
for i,row in enumerate(rows):
    yy=554+i*32
    if i==0:rect(714,yy-18,410,28,PALE,PALE)
    for xx,ss in zip([724,867,1000],row):txt(xx,yy,ss,10,INK,i==0)
    line(714,yy+10,1124,yy+10)
para(714,675,409,'Less than 0.7% change in these integral quantities. This is local stability evidence; it does not establish complete field convergence or real fan performance.',10)
finish()

page(6,'Mesh resolution / local section details','Actual cut mesh over the speed field | Display triangulation includes diagonals added for rendering')
label('01','EXTERNAL FAN / DUCT REGION',38,142);img('mesh_fan',38,158,482,475)
label('02','INTERNAL DUCT / INTAKE DETAIL',533,142);img('mesh_duct',533,158,299,475)
heading(866,165,'MESH INVENTORY')
for j,(a,b) in enumerate([('Cells','836,278'),('Fluid regions','1'),('Maximum skewness','2.496'),('Max non-orthogonality','64.69 deg'),('Minimum determinant','0.000683')]):
    yy=201+j*39;txt(866,yy,a,10,GRAY);txt(866,yy+16,b,13,INK,True)
heading(866,435,'QUALITY DISPOSITION')
para(866,455,266,'Standard checkMesh: Mesh OK. Expanded diagnostics flag one low-determinant cell plus concave cells and warped faces. The surface is closed and passed the self-intersection check.',10)
para(866,568,266,'No prism layers; mesh independence and wall resolution are unverified. Cell faces in the fluid mesh are polyhedral; shown triangles are section-rendering subdivisions.',10)
rect(38,663,1098,75,PALE,PALE)
para(55,676,1060,'<b>Numerical fan thickness:</b> the external actuator zones were broadened from 2 to 10 mm while preserving total force, selecting 2033 / 2032 cells. Internal Dell zones contain 2438 / 2443 cells. Marker bodies are not obstacles. This is a coarse exploratory mesh, not a released validation mesh.',11)
finish()

page(7,'Convergence / evidence and assumptions','First initial residual per field and SIMPLE iteration | Saved result: 1200 | Elapsed solver time: 1166 s')
img('residuals',38,133,760,341)
heading(837,155,'FINAL INITIAL RESIDUALS')
data=json.loads((ASSETS/'plot_provenance.json').read_text())
for i,(k,v) in enumerate(data['final_initial_residuals'].items()):
    yy=187+i*31;txt(839,yy,k,12,INK,True);txt(935,yy,f'{v:.3e}',12,GRAY)
rect(837,394,295,62,'#FFF3E3','#E0C5A0');para(849,405,270,'<b>Iteration limit reached.</b><br/>The 1e-5 residual target was not met.',11,AMBER)
line(38,493,W-38,493)
heading(38,521,'METHOD / PHYSICS')
para(38,541,342,'Steady incompressible SIMPLE; k-omega SST; first-order bounded-upwind momentum. Density 1.2 kg/m3; kinematic viscosity 1.5e-5 m2/s. No-slip walls and zero-gauge-pressure ambient openings.<br/><br/>No thermal transport, CPU heat load, fan P/Q curves, grille porosity or fin-stack resistance. Intake values are uncalibrated model outputs.',10)
heading(421,521,'MODEL / PROVENANCE')
para(421,541,342,'BARAM bundled OpenFOAM v2412, build 6467f461-20260821; Microsoft MPI, eight workers. Warm start from v2 iteration 300.<br/><br/>Source geometry: native mount assembly and traced CFD helper. Profile and intake reconstruction: project profile_reconstruction.json. Final field reconstruction completed normally.',10)
heading(804,521,'SOURCE FILES / REPRODUCTION')
para(804,541,330,'Case: installed_pressure10_v3<br/>Fields: 1200/ and constant/polyMesh/<br/>Log: log.simpleFoam_windows<br/>Samples: results/iteration_1200/flow_samples.json<br/>Views: drawing_assets.py<br/>Layout: build_drawing_package.py<br/><br/>The companion manifest records source hashes, cut planes, units and the PDF digest.',10)
txt(38,745,'Prepared for engineering review. Figures are rendered simulation views, not certified fabrication drawings.',9,GRAY)
finish();c.save()

# Render with MuPDF because Poppler is unavailable in this Windows runtime.
doc=fitz.open(PATH);qa=OUT/'sheets';qa.mkdir(exist_ok=True)
assert len(doc)==7
for i,p in enumerate(doc):
    p.get_pixmap(matrix=fitz.Matrix(150/72,150/72),alpha=False).save(qa/f'sheet_{i+1:02d}.png')
    assert 'EXPLORATORY / NOT CONVERGED' in p.get_text()
sources=[ROOT/'fusion/cfd/cases/OpenCFD_v2412/installed_pressure10_v3/log.simpleFoam_windows',ROOT/'fusion/cfd/cases/OpenCFD_v2412/installed_pressure10_v3/results/iteration_1200/flow_samples.json',ASSETS/'plot_provenance.json',Path(__file__),Path(__file__).with_name('drawing_assets.py')]
manifest={'pdf':PATH.name,'sha256':hashlib.sha256(PATH.read_bytes()).hexdigest(),'pages':7,'page_format':'A3 landscape','render_qa':'MuPDF 1.28.2; per-sheet PNG inspection','sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
(OUT/'drawing_package_manifest.json').write_text(json.dumps(manifest,indent=2))
from zipfile import ZipFile, ZIP_DEFLATED
with ZipFile(OUT/'Precision_5560_CFD_Drawing_Package.zip','w',ZIP_DEFLATED) as z:
    for p in [PATH,OUT/'drawing_package_manifest.json',ASSETS/'plot_provenance.json',*sorted(qa.glob('sheet_*.png'))]:
        z.write(p,p.relative_to(OUT))
from PIL import Image,ImageOps,ImageDraw
contact=Image.new('RGB',(1400,1980),'#E4EBEF')
for i,p in enumerate(sorted(qa.glob('sheet_*.png'))):
    im=Image.open(p);im.thumbnail((690,480))
    contact.paste(im,(5+(i%2)*700,5+(i//2)*495))
contact.save(OUT/'contact_sheet.png')
print(str(PATH))
