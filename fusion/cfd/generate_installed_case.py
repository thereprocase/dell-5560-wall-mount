"""Coarse isothermal four-fan pressure-forcing exploration; uncalibrated hardware."""
from pathlib import Path
import json, math, shutil
from generate_case import foam_header,field,vec,block_mesh
base=Path(__file__).resolve().parent
geom=base/'geometry_traced_repaired';case=base/'cases/OpenCFD_v2412/installed_pressure10_v2'
if case.exists():raise RuntimeError('Preserve existing case')
meta=json.loads((geom/'geometry_manifest.json').read_text())
assert meta['geometry_ready']
assert 'Surface is not self-intersecting' in (geom/'stabilized_8.log').read_text()
for folder in ('0','constant/triSurface','system'):(case/folder).mkdir(parents=True,exist_ok=True)
def put(name,s):
 (case/name).write_text(s)
shutil.copy2(geom/'fluid_stabilized_8.stl',case/'constant/triSurface/fluid_boundary.stl')
patches=['printed','laptop','noctua','wall_plane','ambient_openings']
for name,dimensions,value in [('U','0 1 -1 0 0 0 0','(0 0 0)'),('p','0 2 -2 0 0 0 0','0'),('k','0 2 -2 0 0 0 0','0.01'),('omega','0 0 -1 0 0 0 0','20'),('nut','0 2 -1 0 0 0 0','0')]:
 bc={}
 for patch in patches+['backgroundBox']:
  if patch=='ambient_openings':
   bc[patch]={'U':'type pressureInletOutletVelocity; value uniform (0 0 0);','p':'type fixedValue; value uniform 0;',
    'k':'type inletOutlet; inletValue uniform 0.01; value uniform 0.01;','omega':'type inletOutlet; inletValue uniform 20; value uniform 20;','nut':'type calculated; value uniform 0;'}[name]
  else:
   bc[patch]={'U':'type noSlip;','p':'type zeroGradient;','k':'type kqRWallFunction; value uniform 0.01;','omega':'type omegaWallFunction; value uniform 20;','nut':'type nutkWallFunction; value uniform 0;'}[name]
 put('0/'+name,field(name,dimensions,value,bc))
for name in ('fvSchemes','fvSolution'):
 s=(base/'cases/OpenCFD_v2412/q20_coarse/system'/name).read_text()
 if name=='fvSolution':s=s.replace('U 0.7; k 0.7; omega 0.7;','U 0.5; k 0.5; omega 0.5;')
 put('system/'+name,s)
for name in ('transportProperties','turbulenceProperties'):
 shutil.copy2(base/'cases/OpenCFD_v2412/q20_coarse/constant'/name,case/'constant'/name)
config={'block_mesh_domain_m':{'min':[-.42,-.02,-.32],'max':[.42,.47,.52]}}
# Explicit uniform 20mm background; local refinements resolve narrow passages.
put('system/blockMeshDict',block_mesh(config,{'base_cell_m':.02}))
put('system/controlDict',foam_header('controlDict')+"""
application simpleFoam;
startFrom startTime; startTime 0; stopAt endTime; endTime 600; deltaT 1;
writeControl timeStep; writeInterval 100; purgeWrite 0;
writeFormat binary; writePrecision 10; writeCompression off;
timeFormat general; timePrecision 8; runTimeModifiable true;
functions
{
 extrema {type fieldMinMax; libs (fieldFunctionObjects); fields (U p k omega); writeControl timeStep; writeInterval 20;}
 yPlus {type yPlus; libs (fieldFunctionObjects); writeControl writeTime;}
 ambient_flux {type surfaceFieldValue; libs (fieldFunctionObjects); regionType patch; name ambient_openings; operation sum; fields (phi); writeFields false; writeControl timeStep; writeInterval 20;}
}
""")
regions='\n'.join(f'{p} {{name {p};}}' for p in patches)
levels='\n'.join(f'{p} {{level ({4 if p=="laptop" else 3 if p in ("printed","noctua") else 0} {4 if p=="laptop" else 3 if p in ("printed","noctua") else 0}); patchInfo {{type {"patch" if p=="ambient_openings" else "wall"};}}}}' for p in patches)
layers=(base/'cases/OpenCFD_v2412/q20_coarse/system/snappyHexMeshDict').read_text().split('addLayersControls',1)[1].split('meshQualityControls',1)[0]
quality=(base/'cases/OpenCFD_v2412/q20_coarse/system/snappyHexMeshDict').read_text().split('meshQualityControls',1)[1]
put('system/snappyHexMeshDict',foam_header('snappyHexMeshDict')+f"""
castellatedMesh true; snap true; addLayers false;
geometry {{
 fluid_boundary.stl {{type triSurfaceMesh; name fluid; regions {{{regions}}}}}
 interior {{type searchableBox; min (-0.15 0.038 0.14); max (0.15 0.052 0.235);}}
}}
castellatedMeshControls {{
 maxLocalCells 2000000; maxGlobalCells 4000000; minRefinementCells 0; maxLoadUnbalance 0.1;
 nCellsBetweenLevels 3; features ();
 refinementSurfaces {{fluid {{level (0 0); patchInfo {{type wall;}} regions {{{levels}}}}}}}
 resolveFeatureAngle 30;
 refinementRegions {{interior {{mode inside; levels ((1e15 4));}}}}
 locationInMesh (0 0.25 0.1); allowFreeStandingZoneFaces true;
}}
snapControls {{nSmoothPatch 3; tolerance 2; nSolveIter 30; nRelaxIter 5; nFeatureSnapIter 10; implicitFeatureSnap true; explicitFeatureSnap false; multiRegionFeatureSnap false;}}
addLayersControls {layers}
meshQualityControls {quality}
""")
p=case/'system/snappyHexMeshDict'
p.write_text(p.read_text().replace('maxBoundarySkewness 20','maxBoundarySkewness 2.5').replace('minDeterminant 0.001','minDeterminant 0.01'))
put('system/decomposeParDict',foam_header('decomposeParDict')+'numberOfSubdomains 8; method scotch;')
actions=[];options=[];assumptions=[]
for name,zone in meta['zones'].items():
 if 'fan' not in name:continue
 centre=[v*.001 for v in zone['centroid_mm']];direction=zone['actuator_direction']
 radius=.025 if name.startswith('dell') else .055
 # Native marker thickness2mm. Select the same cylinder; actual selected volume is recorded by topoSet/fvOptions.
 p1=[v-.001*d for v,d in zip(centre,direction)];p2=[v+.001*d for v,d in zip(centre,direction)]
 actions += [f'{{name {name}; type cellSet; action new; source cylinderToCell; p1 {vec(p1)}; p2 {vec(p2)}; radius {radius};}}',f'{{name {name}; type cellZoneSet; action new; source setToCellZone; set {name};}}']
 # Integral acceleration volume = force/rho = pressure rise * disk area / density.
 force=[10*math.pi*radius**2/1.2*d for d in direction]
 options.append(f'{name} {{type vectorSemiImplicitSource; active yes; selectionMode cellZone; cellZone {name}; volumeMode absolute; injectionRateSuSp {{U ({vec(force)} 0);}}}}')
 assumptions.append(dict(name=name,assumed_pressure_Pa=10,area_m2=math.pi*radius**2,direction=direction,integrated_force_over_density=force))
put('system/topoSetDict',foam_header('topoSetDict')+'actions (\n'+'\n'.join(actions)+'\n);')
put('constant/fvOptions',foam_header('fvOptions')+'\n'.join(options))
(case/'case.foam').touch()
p=case/'system/controlDict'
s=p.read_text().rsplit('}',1)[0]
for name in [r['name'] for r in assumptions]:
 s+=f'{name}_mean {{type volFieldValue; libs (fieldFunctionObjects); regionType cellZone; name {name}; operation volAverage; fields (U p); writeFields false; writeControl timeStep; writeInterval 20;}}\n'
p.write_text(s+'}\n')
put('assumptions.json',json.dumps(dict(scope='Uncalibrated, coarse isothermal airflow exploration, not hardware performance or thermal prediction',fan_sources=assumptions,grille_resistance='Zero added resistance; traced gross active opening; unknown porosity',internal_ducts='Assumed simplified paired internal flow passages',mesh='No prism layers in first diagnostic run; wall resolution and mesh sensitivity unverified',density_kg_m3=1.2),indent=2))
print(case)
