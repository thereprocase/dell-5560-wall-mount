"""OpenFOAM steady 2-D RANS screening of a sealed representative fan-band section.
Coordinates here: X=wall-normal Y of mount; Y=vertical Z of mount; Z=span.
This is an external plenum model, not a resolved laptop or thermal simulation.
"""
from pathlib import Path
import math,json,os,subprocess,shutil
OUT=Path(__file__).resolve().parent;ROOT=OUT/'cfd';ROOT.mkdir(exist_ok=True)
RUNTIME=OUT.parent/'cfd-runtime/foam/usr'
def header(obj,cls='dictionary'):
 return f'FoamFile {{ version 2.0; format ascii; class {cls}; object {obj}; }}\n'
def environment():
 e=os.environ.copy()
 if not RUNTIME.exists():return e
 e['PATH']=str(RUNTIME/'bin')+':'+e['PATH'];e['LD_LIBRARY_PATH']=str(RUNTIME/'lib')+':'+str(RUNTIME/'lib/x86_64-linux-gnu')
 e['WM_PROJECT_DIR']=str(RUNTIME/'share/openfoam');e['FOAM_ETC']=str(RUNTIME/'share/openfoam/etc');e['WM_PROJECT_VERSION']='v1912';e['FOAM_LIBBIN']=str(RUNTIME/'lib');return e

def make_case(name,gap=12,curved=True,h=2,pressure=20,draw=.4,iterations=1600):
 case=ROOT/name
 if case.exists():
  for p in case.iterdir():
   if p.is_dir() and (p.name.replace(".","").isdigit() or p.name=="VTK"):shutil.rmtree(p)
 for x in ['system','constant','0']:(case/x).mkdir(parents=True,exist_ok=True)
 # Same fan-plane and outlet interfaces as CAD; smooth-turn intermediate stations.
 levels=[((23,-128),(111,-40))]
 if curved:levels += [((8,-80),(66,-28))]
 levels += [((4,-35),(42,-10)),((4,2),(40,2)),((4,40),(40,40)),((4,100),(40,100)),((4,156),(40,156)),((4,192),(40,192)),((4,198),(40,198)),((4+(36-gap)*20/28,218),(38,218)),((4+(36-gap)*24/28,222),(38,222)),((4+(36-gap)*26/28,224),(40,224)),((40-gap,226),(40,226)),((40-gap,232),(40,232))]
 # Downstream slot extends to hinge height: 6 mm upward guide, matches selected CAD rail.
 n=len(levels);verts=[]
 for depth in [0,1]:
  for L,R in levels:verts += [(L[0]/1000,L[1]/1000,depth*.001),(R[0]/1000,R[1]/1000,depth*.001)]
 nx=max(12,round(36/h));blocks=[];wall=[];vent=[];empty=[]
 for j in range(n-1):
  a=2*j;b=a+1;c=a+3;d=a+2;off=2*n
  dl=math.dist(levels[j][0],levels[j+1][0]);dr=math.dist(levels[j][1],levels[j+1][1]);ny=max(2,round((dl+dr)/2/h))
  blocks.append(f'hex ({a} {b} {c} {d} {a+off} {b+off} {c+off} {d+off}) ({nx} {ny} 1) simpleGrading (1 1 1)')
  wall.append((a,d,d+off,a+off));right=(b,b+off,c+off,c)
  (vent if levels[j][1][1]==156 else wall).append(right)
  empty += [(a,b,c,d),(a+off,d+off,c+off,b+off)]
 def faces(fs):return '\n'.join('('+' '.join(map(str,f))+')' for f in fs)
 inlet=[(0,2*n,2*n+1,1)];a=2*n-2;b=a+1;outlet=[(a,b,b+2*n,a+2*n)]
 patches={'walls':('wall',wall),'laptopVent':('patch',vent),'fanInlet':('patch',inlet),'slotOutlet':('patch',outlet),'frontBack':('empty',empty)}
 mesh=header('blockMeshDict')+'convertToMeters 1;\nvertices (\n'+'\n'.join('(%g %g %g)'%p for p in verts)+');\nblocks (\n'+'\n'.join(blocks)+');\nedges ();\nboundary (\n'
 mesh+='\n'.join(f'{k} {{ type {typ}; faces ( {faces(fs)} ); }}' for k,(typ,fs) in patches.items())+');\nmergePatchPairs ();\n'
 (case/'system/blockMeshDict').write_text(mesh)
 control=header('controlDict')+f'''application simpleFoam; startFrom startTime; startTime 0; stopAt endTime; endTime {iterations}; deltaT 1; writeControl timeStep; writeInterval 100; purgeWrite 2; writeFormat ascii; writePrecision 9; runTimeModifiable false;
functions
{{
 ventPressure {{type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); writeControl timeStep; writeInterval 20; regionType patch; name laptopVent; operation areaAverage; fields (p);}}
 inletFlow {{type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); writeControl timeStep; writeInterval 20; regionType patch; name fanInlet; operation sum; fields (phi);}}
 outletFlow {{type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); writeControl timeStep; writeInterval 20; regionType patch; name slotOutlet; operation sum; fields (phi);}}
 ventFlow {{type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); writeControl timeStep; writeInterval 20; regionType patch; name laptopVent; operation sum; fields (phi);}}
}}
'''
 (case/'system/controlDict').write_text(control)
 (case/'system/fvSchemes').write_text(header('fvSchemes')+'''ddtSchemes {default steadyState;} gradSchemes {default cellLimited Gauss linear 1;} divSchemes {default none; div(phi,U) bounded Gauss linearUpwind grad(U); div(phi,k) bounded Gauss upwind; div(phi,omega) bounded Gauss upwind; div((nuEff*dev2(T(grad(U))))) Gauss linear;} laplacianSchemes {default Gauss linear corrected;} interpolationSchemes {default linear;} snGradSchemes {default corrected;} wallDist {method meshWave;} fluxRequired {default no; p;}
''')
 (case/'system/fvSolution').write_text(header('fvSolution')+'''solvers {p {solver GAMG; tolerance 1e-8; relTol 0.05; smoother GaussSeidel;} "(U|k|omega)" {solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0.05;}} SIMPLE {nNonOrthogonalCorrectors 1; consistent yes; residualControl {p 1e-6; U 1e-6; "(k|omega)" 1e-6;}} relaxationFactors {fields {p 0.25;} equations {U 0.6; k 0.5; omega 0.5;}}\n''')
 (case/'constant/transportProperties').write_text(header('transportProperties')+'transportModel Newtonian; nu [0 2 -1 0 0 0 0] 1.5e-5;\n')
 (case/'constant/turbulenceProperties').write_text(header('turbulenceProperties')+'simulationType RAS; RAS {RASModel kOmegaSST; turbulence on; printCoeffs on;}\n')
 def field(n,dim,value,bc,vector=False):
  typ='volVectorField' if vector else 'volScalarField'
  (case/'0'/n).write_text(header(n,typ)+f'dimensions {dim}; internalField uniform {value};\nboundaryField {{\n'+''.join(f'{p} {{ {bc[p]} }}\n' for p in patches)+'}\n')
 field('p','[0 2 -2 0 0 0 0]','0',dict(walls='type zeroGradient;',laptopVent='type zeroGradient;',fanInlet=f'type totalPressure; p0 uniform {pressure/1.2}; value uniform {pressure/1.2};',slotOutlet='type fixedValue; value uniform 0;',frontBack='type empty;'))
 field('U','[0 1 -1 0 0 0 0]','(0 0.1 0)',dict(walls='type noSlip;',laptopVent=f'type fixedValue; value uniform ({draw} 0 0);',fanInlet='type pressureInletOutletVelocity; value uniform (-1 1 0);',slotOutlet='type inletOutlet; inletValue uniform (0 0 0); value uniform (0 1 0);',frontBack='type empty;'),True)
 for n,value,dim,wall in [('k','.015','[0 2 -2 0 0 0 0]','kqRWallFunction'),('omega','50','[0 0 -1 0 0 0 0]','omegaWallFunction'),('nut','0','[0 2 -1 0 0 0 0]','nutkWallFunction')]:
  field(n,dim,value,dict(walls=f'type {wall}; value uniform {value};',laptopVent='type zeroGradient;',fanInlet=(f'type fixedValue; value uniform {value};' if n!='nut' else 'type calculated; value uniform 0;'),slotOutlet=(f'type inletOutlet; inletValue uniform {value}; value uniform {value};' if n!='nut' else 'type calculated; value uniform 0;'),frontBack='type empty;'))
 (case/'case_parameters.json').write_text(json.dumps(dict(name=name,gap_mm=gap,curved=curved,nominal_mesh_mm=h,total_pressure_Pa=pressure,vent_draw_m_s=draw,rho=1.2,levels_mm=levels),indent=2))
 return case

def run(case):
 for cmd in ['blockMesh','checkMesh','simpleFoam']:
  with (case/(cmd+'.log')).open('w') as f:
   r=subprocess.run([cmd,*(['-noFunctionObjects'] if cmd=='simpleFoam' else []),'-case',str(case)],env=environment(),stdout=f,stderr=subprocess.STDOUT)
  if r.returncode:raise RuntimeError(str(case)+' '+cmd+' failed')
 print(case.name,'completed',flush=True)
if __name__=='__main__':
 import sys
 n=sys.argv[1] if len(sys.argv)>1 else 'curved_12_coarse'
 run(make_case(n))
