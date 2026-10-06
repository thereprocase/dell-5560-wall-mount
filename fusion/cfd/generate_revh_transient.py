"""Generate an isolated Rev H mesh and transient SST case; never reuse a run."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import random
import math
from datetime import datetime, timezone
from generate_case import foam_header, field, combined_stl, read_triangles, dot, cross, sub

BASE = Path(__file__).resolve().parent
PATCHES = ('printed', 'laptop', 'noctua', 'wall_plane', 'ambient_openings')


def generate(case, geometry, perturb_m=0):
    meta = json.loads((geometry / 'geometry_manifest.json').read_text())
    assert meta['geometry_ready'] and meta['all_zone_volumes_inside_fluid']
    case.mkdir(parents=True, exist_ok=False)
    for name in ('0', 'constant/triSurface', 'system', 'config'):
        (case / name).mkdir(parents=True)

    def put(name, text):
        (case / name).write_text(text, encoding='ascii', newline='\n')

    def dictionary(name, text):
        put('system/' + name, foam_header(name) + text)

    patches = {p: read_triangles(geometry / (p+'.stl')) for p in PATCHES}
    repair = None
    if perturb_m:
        assert 0 < perturb_m <= 1e-8, 'Perturbation must be bounded at 10 nm per coordinate'
        rng=random.Random(5560)
        mapping={}
        for tris in patches.values():
            for tri in tris:
                for p in tri:
                    if p not in mapping:
                        fixed={i:v for i,v in [(0,-.4),(0,.4),(1,0),(1,.45),(2,-.3),(2,.5)] if abs(p[i]-v)<1e-12}
                        mapping[p]=tuple(fixed[i] if i in fixed else v+perturb_m*rng.uniform(-1,1) for i,v in enumerate(p))
        moved={n:[tuple(mapping[p] for p in tri) for tri in tris] for n,tris in patches.items()}
        flips=sum(dot(cross(sub(a[1],a[0]),sub(a[2],a[0])),cross(sub(b[1],b[0]),sub(b[2],b[0])))<=0
                  for n in patches for a,b in zip(patches[n],moved[n]))
        assert flips==0
        repair={'method':'Deterministic sub-micrometre vertex perturbation; domain planes fixed; native CAD unchanged',
                'seed':5560,'max_displacement_m':max(math.dist(p,q) for p,q in mapping.items()),'flipped_normals':flips}
        patches=moved
    surface = combined_stl(patches)
    put('constant/triSurface/fluid_boundary.stl', surface)
    old = BASE / 'cases/OpenCFD_v2412/installed_pressure10_v3'
    for name in ('transportProperties', 'turbulenceProperties', 'fvOptions'):
        shutil.copy2(old / 'constant' / name, case / 'constant' / name)
    shutil.copy2(old / 'system/topoSetDict', case / 'system/topoSetDict')
    for name, dimensions, value in [('U','0 1 -1 0 0 0 0','(0 0 0)'),
                                    ('p','0 2 -2 0 0 0 0','0'),
                                    ('k','0 2 -2 0 0 0 0','0.01'),
                                    ('omega','0 0 -1 0 0 0 0','20'),
                                    ('nut','0 2 -1 0 0 0 0','0')]:
        bc = {}
        for patch in (*PATCHES, 'backgroundBox'):
            if patch == 'ambient_openings':
                bc[patch] = {'U':'type pressureInletOutletVelocity; value uniform (0 0 0);',
                    'p':'type fixedValue; value uniform 0;',
                    'k':'type inletOutlet; inletValue uniform 0.01; value uniform 0.01;',
                    'omega':'type inletOutlet; inletValue uniform 20; value uniform 20;',
                    'nut':'type calculated; value uniform 0;'}[name]
            else:
                bc[patch] = {'U':'type noSlip;', 'p':'type zeroGradient;',
                    'k':'type kqRWallFunction; value uniform 0.01;',
                    'omega':'type omegaWallFunction; value uniform 20;',
                    'nut':'type nutUSpaldingWallFunction; value uniform 0;'}[name]
        put('0/' + name, field(name, dimensions, value, bc))

    dictionary('blockMeshDict', '''
scale 1;
vertices ((-.432 -.032 -.336) (.432 -.032 -.336) (.432 .480 -.336) (-.432 .480 -.336)
          (-.432 -.032 .528) (.432 -.032 .528) (.432 .480 .528) (-.432 .480 .528));
blocks (hex (0 1 2 3 4 5 6 7) (54 32 54) simpleGrading (1 1 1));
edges ();
boundary (backgroundBox {type wall; faces ((0 4 7 3) (1 2 6 5) (0 1 5 4) (3 7 6 2) (0 3 2 1) (4 5 6 7));});
mergePatchPairs ();
''')
    # Refinement boxes include both free shear-layer space and sharp solid edges.
    boxes = {
        'ductWake': ((-.145,.002,-.004),(.145,.042,.024),5),
        'ductOuterEdge': ((-.145,.034,-.004),(.145,.043,.010),6),
        'frontLip': ((-.174,.047,-.003),(.174,.058,.009),6),
        'frontLipWake': ((-.176,.042,-.002),(.176,.064,.022),5),
        'leftPassage': ((-.150,.037,.140),(-.073,.052,.238),5),
        'rightPassage': ((.073,.037,.140),(.150,.052,.238),5),
        'leftHingeLip': ((-.150,.037,.222),(-.073,.054,.237),6),
        'rightHingeLip': ((.073,.037,.222),(.150,.054,.237),6),
        'hingeWake': ((-.150,.033,.232),(.150,.061,.253),5),
        'leftDuctSide': ((-.145,.003,-.008),(-.136,.044,.014),6),
        'rightDuctSide': ((.136,.003,-.008),(.145,.044,.014),6),
    }
    def vec(p): return '('+' '.join(str(v) for v in p)+')'
    shapes = '\n'.join(f'{k} {{type searchableBox; min {vec(a)}; max {vec(b)};}}' for k,(a,b,l) in boxes.items())
    refinements = '\n'.join(f'{k} {{mode inside; levels ((1e15 {l}));}}' for k,(a,b,l) in boxes.items())
    regions = '\n'.join(f'{p} {{name {p};}}' for p in PATCHES)
    levels = '\n'.join(f'{p} {{level ({l} {l}); patchInfo {{type {"patch" if p=="ambient_openings" else "wall"};}}}}'
                       for p,l in zip(PATCHES,(4,4,3,0,0)))
    dictionary('snappyHexMeshDict', f'''
castellatedMesh true; snap true; addLayers true;
geometry {{
 fluid_boundary.stl {{type triSurfaceMesh; name fluid; regions {{{regions}}}}}
 {shapes}
}}
castellatedMeshControls {{
 maxLocalCells 6000000; maxGlobalCells 24000000; minRefinementCells 0; maxLoadUnbalance .10;
 nCellsBetweenLevels 3; features ();
 refinementSurfaces {{fluid {{level (0 0); regions {{{levels}}}}}}}
 resolveFeatureAngle 30;
 refinementRegions {{{refinements}}}
 locationInMesh (0 .25 .1); allowFreeStandingZoneFaces true;
}}
snapControls {{nSmoothPatch 5; tolerance 1.5; nSolveIter 50; nRelaxIter 8;
 nFeatureSnapIter 15; implicitFeatureSnap true; explicitFeatureSnap false; multiRegionFeatureSnap false;}}
addLayersControls {{
 relativeSizes false;
 layers {{printed {{nSurfaceLayers 5;}} laptop {{nSurfaceLayers 5;}} noctua {{nSurfaceLayers 3;}}}}
 expansionRatio 1.2; firstLayerThickness .00006; minThickness .00002;
 nGrow 0; featureAngle 60; nRelaxIter 8;
 nSmoothSurfaceNormals 1; nSmoothNormals 3; nSmoothThickness 10;
 maxFaceThicknessRatio .5; maxThicknessToMedialRatio .3; minMedialAxisAngle 90;
 nBufferCellsNoExtrude 1; nLayerIter 60;
}}
meshQualityControls {{
 maxNonOrtho 65; maxBoundarySkewness 2.5; maxInternalSkewness 4;
 maxConcave 80; minVol 1e-18; minTetQuality 1e-15; minArea -1;
 minTwist .02; minDeterminant .01; minFaceWeight .05; minVolRatio .01;
 minTriangleTwist -1; nSmoothScale 4; errorReduction .75;
}}
writeFlags (scalarLevels layerSets layerFields);
mergeTolerance 1e-7;
''')
    dictionary('decomposeParDict', 'numberOfSubdomains 8; method scotch;\n')
    schemes = '''
ddtSchemes {default backward;}
gradSchemes {default Gauss linear; grad(U) cellLimited Gauss linear 1;}
divSchemes {
 default none;
 div(phi,U) Gauss linearUpwind grad(U);
 div(phi,k) Gauss upwind;
 div(phi,omega) Gauss upwind;
 div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes {default Gauss linear limited .5;}
interpolationSchemes {default linear;}
snGradSchemes {default limited .5;}
wallDist {method meshWave;}
fluxRequired {default no; p;}
'''
    dictionary('fvSchemes', schemes)
    dictionary('fvSolution', '''
solvers {
 p {solver GAMG; tolerance 1e-8; relTol .03; smoother GaussSeidel;}
 pFinal {$p; relTol 0;}
 "(U|k|omega)" {solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol .05;}
 "(U|k|omega)Final" {solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol 0;}
}
PIMPLE {nOuterCorrectors 3; nCorrectors 2; nNonOrthogonalCorrectors 1; momentumPredictor yes;}
relaxationFactors {equations {".*" 1;}}
''')
    probes = []
    for x in (-.111, .070, .111):
        for y,z,role in [(.039,.008,'duct_edge'),(.039,.020,'duct_wake'),
                         (.046,.004,'front_lip_wallside'),(.060,.004,'front_lip_outside'),
                         (.037,.219,'hinge_underside'),(.046,.239,'hinge_exit'),
                         (.046,.250,'hinge_wake')]:
            probes.append({'name':f'{role}_x{x}', 'point_m':[x,y,z]})
    probes.append({'name':'ambient_reference','point_m':[0,.25,.1]})
    locations = '\n'.join(vec(p['point_m']) for p in probes)
    control = f'''
application pimpleFoam;
startFrom latestTime; startTime 0; stopAt endTime; endTime .002; deltaT .00001;
adjustTimeStep yes; maxCo .5; maxDeltaT .000025;
writeControl adjustableRunTime; writeInterval .001; purgeWrite 0;
writeFormat binary; writePrecision 10; writeCompression off;
timeFormat general; timePrecision 10; runTimeModifiable false;
functions {{
 probes {{type probes; libs (sampling); fields (p U); interpolationScheme cellPoint;
  writeControl timeStep; writeInterval 1; probeLocations ({locations});}}
 extrema {{type fieldMinMax; libs (fieldFunctionObjects); fields (U p k omega); writeControl timeStep; writeInterval 20;}}
 yPlus {{type yPlus; libs (fieldFunctionObjects); executeControl writeTime; writeControl writeTime;}}
 vorticity {{type vorticity; libs (fieldFunctionObjects); executeControl timeStep; executeInterval 1; writeControl writeTime;}}
 Q {{type Q; libs (fieldFunctionObjects); executeControl timeStep; executeInterval 1; writeControl writeTime;}}
 ambient_flux {{type surfaceFieldValue; libs (fieldFunctionObjects); regionType patch; name ambient_openings;
  operation sum; fields (phi); writeFields false; writeControl timeStep; writeInterval 10;}}
 ambient_abs_flux {{type surfaceFieldValue; libs (fieldFunctionObjects); regionType patch; name ambient_openings;
  operation sumMag; fields (phi); writeFields false; writeControl timeStep; writeInterval 10;}}
}}
'''
    dictionary('controlDict', control)
    (case / 'case.foam').touch()
    for name in ('fvSchemes','fvSolution','controlDict'):
        shutil.copy2(case/'system'/name, case/'config'/(name+'.transient'))
    manifest = {
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'geometry_revision': 'H', 'base_commit':'f47a03f',
        'scope':'Transient SST URANS verification candidate; uncalibrated fan forces and surrogate laptop; no heat transfer.',
        'geometry_inputs':meta['inputs'],
        'laptop_geometry_uncertainty_mm':{'profile':meta['trace']['data']['profile_estimated_uncertainty_mm'],
                                          'intake_location':meta['trace']['data']['intake_location_uncertainty_mm']},
        'surface_sha256':hashlib.sha256(surface.encode('ascii')).hexdigest(),
        'numerical_surface_stabilization':repair,
        'surface_deflection_mm':.025, 'base_cell_mm':16,
        'surface_cell_mm':{'printed':1,'laptop':1,'noctua':2},
        'refinement_boxes':{k:{'min_m':a,'max_m':b,'level':l,'cell_mm':16/2**l} for k,(a,b,l) in boxes.items()},
        'requested_layers':{'printed':5,'laptop':5,'noctua':3,'first_layer_thickness_mm':.06,'growth':1.2},
        'requested_max_Co':.5,'requested_max_deltaT_s':.000025,
        'pilot_end_time_s':.002,
        'production_plan':'Assess pilot runtime, probe validity, local mesh and yPlus; map coarse fields only as initialization. Extend through startup then >=20 measured shedding periods; halve time step and refine mesh before any convergence claim.',
        'probes':probes,
        'interpretation':'Look for sustained traveling vorticity and reproducible pressure spectra; do not infer shedding from a still streamline image. Gauge p in Pa = 1.2 * p. Pressure depression alone does not establish a Bernoulli cause.',
        'gates':{'surface':False,'mesh':False,'layers':False,'transient_pilot':False,'spatial_convergence':False,'temporal_convergence':False,'hardware_validation':False},
    }
    (case/'case_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(case)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',type=Path,default=BASE/'runs/revh_transient_01')
    parser.add_argument('--geometry',type=Path,default=BASE/'geometry_revh')
    parser.add_argument('--perturb-m',type=float,default=0)
    args=parser.parse_args()
    generate(args.case.resolve(),args.geometry.resolve(),args.perturb_m)
