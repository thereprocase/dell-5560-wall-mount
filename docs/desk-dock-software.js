// Canvas fallback for browsers without WebGL. Uses the same CAD geometry and controls.
import * as THREE from 'three';
export class SoftwareRenderer {
 constructor(canvas){this.canvas=canvas;this.ctx=canvas.getContext('2d');this.cache=new WeakMap();this.last='';}
 setPixelRatio(){}
 setSize(w,h){this.canvas.width=Math.round(w);this.canvas.height=Math.round(h);this.last='';}
 render(scene,camera){scene.updateMatrixWorld();camera.updateMatrixWorld();const signature=camera.matrixWorld.elements.join(',')+camera.aspect+scene.children.filter(m=>m.isMesh).map(m=>m.visible+':'+m.position.toArray()+':'+m.material.emissive?.getHex()).join(';');if(signature===this.last)return;this.last=signature;
 const ctx=this.ctx,w=this.canvas.width,h=this.canvas.height;ctx.fillStyle='#182a31';ctx.fillRect(0,0,w,h);const faces=[],matrix=new THREE.Matrix4(),vp=new THREE.Matrix4().multiplyMatrices(camera.projectionMatrix,camera.matrixWorldInverse),light=new THREE.Vector3(.3,.6,1).normalize();
 scene.traverseVisible(m=>{if(!m.isMesh)return;const g=m.geometry,pos=g.attributes.position;if(!pos)return;let cache=this.cache.get(m);
 if(!cache){const idx=g.index?.array||Uint32Array.from({length:pos.count},(_,i)=>i);const shade=new Float32Array(idx.length/3),v=new THREE.Vector3(),a=new THREE.Vector3(),b=new THREE.Vector3();for(let f=0;f<idx.length;f+=3){a.fromBufferAttribute(pos,idx[f]);b.fromBufferAttribute(pos,idx[f+1]).sub(a);v.fromBufferAttribute(pos,idx[f+2]).sub(a);shade[f/3]=.52+.48*Math.max(0,b.cross(v).normalize().dot(light));}cache={idx,shade,projected:new Float32Array(pos.count*3)};this.cache.set(m,cache);}
 matrix.multiplyMatrices(vp,m.matrixWorld);const e=matrix.elements,p=pos.array,t=cache.projected;for(let i=0;i<p.length;i+=3){const x=p[i],y=p[i+1],z=p[i+2],q=e[3]*x+e[7]*y+e[11]*z+e[15];t[i]=(1+(e[0]*x+e[4]*y+e[8]*z+e[12])/q)*w/2;t[i+1]=(1-(e[1]*x+e[5]*y+e[9]*z+e[13])/q)*h/2;t[i+2]=(e[2]*x+e[6]*y+e[10]*z+e[14])/q;}
 const c=m.material.color.clone().convertLinearToSRGB(),highlight=m.material.emissive?.getHex()>0;const colors=Array.from({length:20},(_,i)=>{const s=.52+i*.48/19;return `rgb(${Math.min(255,c.r*255*s+(highlight?25:0))},${Math.min(255,c.g*255*s+(highlight?50:0))},${Math.min(255,c.b*255*s+(highlight?35:0))})`;});
 for(let f=0;f<cache.idx.length;f+=3){const a=cache.idx[f]*3,b=cache.idx[f+1]*3,c=cache.idx[f+2]*3;const area=(t[b]-t[a])*(t[c+1]-t[a+1])-(t[b+1]-t[a+1])*(t[c]-t[a]);if(area>=0||t[a+2]>1||t[b+2]>1||t[c+2]>1||t[a+2]<-1)continue;faces.push([t,a,b,c,(t[a+2]+t[b+2]+t[c+2])/3,colors[Math.round((cache.shade[f/3]-.52)/.48*19)]]);}});
 faces.sort((a,b)=>b[4]-a[4]);for(const [t,a,b,c,z,color] of faces){ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(t[a],t[a+1]);ctx.lineTo(t[b],t[b+1]);ctx.lineTo(t[c],t[c+1]);ctx.closePath();ctx.fill();}
 }
}
