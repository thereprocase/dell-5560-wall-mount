"""Flatten only printable 3MF meshes, excluding support enforcers."""
from pathlib import Path
import hashlib,json,zipfile,xml.etree.ElementTree as E
import numpy as np
from scipy.spatial import cKDTree
work=Path(__file__).resolve().parent
NS='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
identity=[1,0,0,0,1,0,0,0,1,0,0,0]
def flatten(path):
    verts=[];faces=[]
    with zipfile.ZipFile(path) as z:
        documents={}
        excluded=set()
        if 'Metadata/model_settings.config' in z.namelist():
            cfg=E.fromstring(z.read('Metadata/model_settings.config'))
            excluded={p.get('id') for p in cfg.findall('.//part') if p.get('subtype','normal_part')!='normal_part'}
        def doc(name):
            if name not in documents:documents[name]=E.fromstring(z.read(name))
            return documents[name]
        def walk(name,oid,transforms):
            if oid in excluded:return
            obj=next(o for o in doc(name).find(NS+'resources').findall(NS+'object') if o.get('id')==oid)
            mesh=obj.find(NS+'mesh')
            if mesh is not None:
                v=np.array([[float(n.get(k)) for k in ['x','y','z']] for n in mesh.find(NS+'vertices')])
                for t in transforms:v = v @ np.array(t[:9]).reshape(3,3)+np.array(t[9:])
                start=len(verts);verts.extend(v.tolist())
                faces.extend(tuple(start+int(n.get(k)) for k in ['v1','v2','v3']) for n in mesh.find(NS+'triangles'))
            else:
                for c in obj.find(NS+'components'):
                    target=next((v.lstrip('/') for k,v in c.attrib.items() if k.endswith('}path')),name)
                    t=[float(x) for x in c.get('transform',' '.join(map(str,identity))).split()]
                    walk(target,c.get('objectid'),[t]+transforms)
        for item in doc('3D/3dmodel.model').find(NS+'build'):
            t=[float(x) for x in item.get('transform',' '.join(map(str,identity))).split()]
            walk('3D/3dmodel.model',item.get('objectid'),[t])
    return np.array(verts),faces
