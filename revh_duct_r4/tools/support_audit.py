"""Geometric screen with explicit support-contact gap and actual deposition Z."""
from pathlib import Path
import collections,hashlib,json,math,re,sys
from shapely.geometry import LineString
from shapely.ops import unary_union
from shapely.prepared import prep
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'minimalist'))
from gcode_audit import lines

def read_paths(path):
    layers=collections.defaultdict(list);x=y=z=e_position=0.;width=.42;feature='';relative=True;active=False;header=[]
    for line in path.open():
        if line.startswith(';'):header.append(line.rstrip())
        if line.startswith('; Z_HEIGHT:'):active=True
        if line.startswith('; FEATURE:'):feature=line.split(':',1)[1].strip()
        if line.startswith('; LINE_WIDTH:'):width=float(line.split(':')[1])
        code=line.split(';')[0].strip()
        if not code:continue
        command=code.split()[0]
        if command=='M83':relative=True
        if command=='M82':relative=False
        vals={k:float(v) for k,v in re.findall(r'([XYZEIJ])(-?\d*\.?\d+)',code)}
        if command=='G92':e_position=vals.get('E',e_position)
        if command not in ('G0','G1','G2','G3'):continue
        # Z is parsed separately because support interfaces can have different Z
        # from the latest model-layer comment.
        zz=re.search(r'(?:^|\s)Z(-?\d*\.?\d+)',code);nz=float(zz[1]) if zz else z
        nx,ny=vals.get('X',x),vals.get('Y',y)
        extrusion=vals.get('E',0 if relative else e_position);delta=extrusion if relative else extrusion-e_position
        if 'E' in vals:e_position=e_position+extrusion if relative else extrusion
        if active and delta>0 and (nx!=x or ny!=y) and feature not in ('Custom','Brim','Flush','Skirt'):
            assert abs(nz-z)<.0002,'Extruding sloped move requires a 3D audit'
            points=[(x,y),(nx,ny)]
            if command in ('G2','G3'):
                cx,cy=x+vals.get('I',0),y+vals.get('J',0);a,b=math.atan2(y-cy,x-cx),math.atan2(ny-cy,nx-cx)
                angle=(b-a)%(2*math.pi)
                if command=='G2':angle-=2*math.pi
                radius=math.hypot(x-cx,y-cy);n=max(2,math.ceil(abs(angle)*radius/.1))
                points=[(cx+radius*math.cos(a+angle*i/n),cy+radius*math.sin(a+angle*i/n)) for i in range(n+1)]
            layers[round(nz,4)].append((points,width,feature))
        x,y,z=nx,ny,nz
    return layers,header

def audit(path,plot):
    layers,header=read_paths(path);footprints={};model_footprints={};support_footprints={}
    for z,paths in layers.items():
        for dest,want in [(model_footprints,False),(support_footprints,True)]:
            pp=[LineString(p).buffer(w/2,quad_segs=2) for p,w,f in paths if f.startswith('Support')==want]
            if pp:dest[z]=unary_union(pp)
    result={'source_gcode':path.name,'source_gcode_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
       'layers':len(model_footprints),'actual_deposition_z_levels':len(layers),
       'method':'Actual G0/G1/G2/G3 nozzle Z, including support interfaces. Model paths are screened against the preceding model layer and support within 0.40 mm below the current top (0.20 mm layer plus 0.20 mm configured removable contact gap). Support paths are screened against model/support deposited within 0.40 mm below. A bead must overlap the lower footprint by 0.05 mm. Same-layer printing order, ASA sag, support removal and physical strength are not proven.',
       'configured_contact_gap_mm':.2,'floating_components':[],'support_floating_components':[],
       'unsupported_by_feature_mm':{},'max_support_path_span_mm':0,'support_bounds_xyz_mm':None}
    allrows=[];bridges=[];worst=None;supportcoords=[]
    model_z=sorted(model_footprints)
    for z,paths in sorted(layers.items()):
        prior_model_z=max((q for q in model_z if q<z-.0001),default=None)
        lower_model=model_footprints[prior_model_z] if prior_model_z is not None and z-prior_model_z<=.4001 else None
        nearby_support=[v for q,v in support_footprints.items() if .0001<z-q<=.4001]
        model_support=unary_union(([lower_model] if lower_model is not None else [])+nearby_support)
        nearby_all=[v for dd in [model_footprints,support_footprints] for q,v in dd.items() if .0001<z-q<=.4001]
        support_support=unary_union(nearby_all)
        if z>min(layers)+.0001:
            for source,lower,key in [(model_footprints,model_support,'floating_components'),(support_footprints,support_support,'support_floating_components')]:
                if z not in source:continue
                for poly in getattr(source[z],'geoms',[source[z]]):
                    if poly.area>.2 and not poly.intersects(lower.buffer(.15)):
                        result[key].append({'z_mm':z,'area_mm2':poly.area,'bounds_xy_mm':list(poly.bounds)})
        cache={}
        for p,w,f in paths:
            is_support=f.startswith('Support')
            if is_support:supportcoords.extend((x,y,z) for x,y in p)
            if z==min(layers):continue
            low=support_support if is_support else model_support
            ck=(is_support,w)
            if ck not in cache:
                buf=low.buffer(max(0,w/2-.05));cache[ck]=(buf,prep(buf))
            buf,prepared=cache[ck];line=LineString(p)
            unsupported=[] if prepared.covers(line) else lines(line.difference(buf))
            length=max((s.length for s in unsupported),default=0.)
            if is_support:
                result['max_support_path_span_mm']=max(result['max_support_path_span_mm'],length);continue
            row={'z_mm':z,'move_length_mm':line.length,'unsupported_length_mm':length,'unsupported_total_mm':sum(s.length for s in unsupported),'feature':f}
            if 'bridge' in f.lower():bridges.append(row)
            if length>1e-5:
                allrows.append(row);result['unsupported_by_feature_mm'][f]=max(result['unsupported_by_feature_mm'].get(f,0),length)
            if worst is None or length>worst[0]:worst=(length,z,paths,low,unsupported,p)
    result.update(max_unsupported_deposition_span_mm=max((r['unsupported_length_mm'] for r in allrows),default=0),
                  max_unsupported_bridge_span_mm=max((r['unsupported_length_mm'] for r in bridges),default=0),
                  max_bridge_move_mm=max((r['move_length_mm'] for r in bridges),default=0),bridge_path_count=len(bridges),
                  bridge_layers=sorted({r['z_mm'] for r in bridges}),longest_bridges=sorted(bridges,key=lambda r:-r['unsupported_length_mm'])[:20],
                  longest_unsupported_paths=sorted(allrows,key=lambda r:-r['unsupported_length_mm'])[:20],
                  time_and_material_comments=[s for s in header if any(k in s for k in ['model printing time:','filament used [g]','filament used [mm]'])])
    if supportcoords:result['support_bounds_xyz_mm']=[[min(p[i] for p in supportcoords) for i in range(3)],[max(p[i] for p in supportcoords) for i in range(3)]]
    assert supportcoords,'Manual support was not generated'
    if plot:
        import matplotlib;matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.collections import LineCollection
        fig,axes=plt.subplots(1,2,figsize=(13,6))
        # The useful review target is the formerly unsupported ledge at Z 41.8.
        z=41.8;prior=max(q for q in model_footprints if q<z-.0001)
        for ax in axes:
            for dd,col in [(model_footprints,'#d5ddd9'),(support_footprints,'#bb9fd0')]:
                for zz,v in dd.items():
                    if (dd is model_footprints and zz==prior) or (dd is support_footprints and .0001<z-zz<=.4001):
                        for poly in getattr(v,'geoms',[v]):
                            xs,ys=poly.exterior.xy;ax.fill(xs,ys,color=col)
            ax.add_collection(LineCollection([p for p,w,f in layers[z] if not f.startswith('Support')],colors='#1c8489',linewidths=.65))
            ax.autoscale();ax.set_aspect('equal');ax.set_xlabel('Plate X / mm');ax.set_ylabel('Plate Y / mm');ax.set_facecolor('#f7f7f2')
        bound=result['support_bounds_xyz_mm'];axes[1].set_xlim(bound[0][0]-3,bound[1][0]+8);axes[1].set_ylim(bound[0][1]-5,bound[1][1]+5)
        axes[0].set_title('Duct ledge at Z = 41.8 mm');axes[1].set_title('Removable support under the external ledge')
        fig.suptitle('Teal: duct paths   Gray: preceding duct layer   Purple: support contact below the ledge\n0.20 mm removable contact gap; supports stay outside the air passage',fontsize=11)
        fig.tight_layout();fig.savefig(plot,dpi=150);plt.close(fig)
    return result

if __name__=='__main__':
 work=Path(__file__).resolve().parent
 for key in ['03_left_fan_duct','04_right_fan_duct']:
    r=audit(work/'duct-slices'/key/'preview.gcode',work/'reports'/(key+'-final-toolpath.png'))
    (work/'reports'/(key+'-final-toolpath.json')).write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ['source_gcode_sha256','max_unsupported_deposition_span_mm','max_support_path_span_mm','floating_components','support_floating_components','support_bounds_xyz_mm']}),flush=True)
