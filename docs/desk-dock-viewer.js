import * as THREE from 'three';
import {OrbitControls} from './vendor/OrbitControls.js';
const $=id=>document.getElementById(id),canvas=$('scene');
const scene=new THREE.Scene();scene.background=new THREE.Color('#182a31');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));
const camera=new THREE.PerspectiveCamera(36,1,1,4000);camera.up.set(0,0,1);
const controls=new OrbitControls(camera,canvas);controls.enableDamping=true;
scene.add(new THREE.HemisphereLight(0xeaf8ff,0x344247,2.5));
for(const [p,i] of [[[200,400,700],3],[[-400,-200,300],2]]){const l=new THREE.DirectionalLight(0xffffff,i);l.position.set(...p);scene.add(l);}
const meshes=[],air=new THREE.Group();scene.add(air);air.visible=false;
const fan=n=>/fan|blade|outlet_guard/.test(n),moving=n=>n==='Precision_5680_REFERENCE'||n.startsWith('RUBBER_FOOT_');
const pretty=n=>n.replace(/_REFERENCE/g,' (reference)').replaceAll('_',' ');
let playing=false,start=0,selected=null;
function stop(){playing=false;$('play').textContent='▶ Play insertion / removal';}
function offset(p){const n=p.name,s=p.center[0]>177?1:-1;if(moving(n))return [-18,Math.sin(Math.PI/90)*145,Math.cos(Math.PI/90)*145];
if(n.includes('manifold'))return [s*62,0,0];if(n.includes('foot_'))return [s*62,0,-18];
if(n.includes('cover'))return [65,15,115];if(n.includes('guard'))return [s*62,130,35];if(n.includes('bezel'))return [s*62,100,27];if(fan(n))return [s*62,60,16];
if(n.includes('seal')||n.includes('corner_pad'))return [s*62,0,35];
if(n.startsWith('Z_'))return [40,-45,30];if(n.startsWith('Y_'))return [75,0,30];if(n.startsWith('X_'))return [110,0,30];return [145,0,35];}
function update(){const e=+$('explode').value/100,t=+$('motion').value/100;
$('explodeValue').textContent=Math.round(e*100)+'%';const lift=Math.max(0,(t-.2)/.8)*135,x=-18*Math.min(1,t/.2);
$('motionValue').textContent=t===0?'Seated':lift>0?Math.round(lift)+' mm lift':Math.abs(x).toFixed(1)+' mm slide';
$('state').textContent=e>0?'Exploded assembly':lift>0?'Lift / lower along the guides':t>0?'Slide clear of the far-side plug':'Docked · lid toward you';
for(const m of meshes){const p=m.userData;m.position.set(...p.explode).multiplyScalar(e);if(moving(p.name)&&!e)m.position.set(x,Math.sin(Math.PI/90)*lift,Math.cos(Math.PI/90)*lift);
m.visible=(!moving(p.name)||$('laptop').checked)&&(!p.name.includes('adjustment_cover')||$('cover').checked)&&(!fan(p.name)||$('fans').checked);}
air.visible=$('air').checked&&e===0;
}
function view(name){const views={home:[[650,800,470],[185,35,145]],lid:[[177,930,240],[177,30,155]],under:[[100,-880,410],[177,0,155]],plug:[[570,220,210],[378,0,125]]};const [p,t]=views[name];camera.position.set(...p);controls.target.set(...t);controls.update();}
function select(m){if(selected)selected.material.emissive.setHex(0);selected=m;if(m){m.material.emissive.setHex(0x235549);$('part').value=m.userData.name;const n=m.userData.name;let d=moving(n)?'Moving laptop / rubber-foot reference. The closed envelope is simplified; the heel contacts are derived from Dell mesh sections.':n.includes('manifold')?'Curved exhaust plenum with integrated fixed guide and open intake ribs. The exploded view separates the two body halves.':fan(n)?'120 × 15 mm fan assembly, rounded bezel or wire guard. Discharge is 15° above the desk.':n.includes('cover')?'Removable cover over the plug adjustment station. Toggle it off to inspect the adjustment stages.':n.startsWith('Z_')?'Height adjustment and locking hardware: ±5 mm nominal range.':n.startsWith('Y_')?'Lateral adjustment and locking hardware: ±3 mm nominal range.':n.startsWith('X_')?'Insertion-depth adjustment and locking hardware: ±5 mm nominal range.':n.includes('stop')?'Independent chassis stop. Set it after plug alignment so the connector does not carry the seating load.':'Separate component from the D5 CAD model; see the CAD notes for fit and prototype limitations.';$('detail').textContent=pretty(n)+'. '+d;}}
try{
const [manifest,buffer]=await Promise.all([fetch('models/desk-dock-d5/model.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json();}),fetch('models/desk-dock-d5/model.bin').then(r=>{if(!r.ok)throw Error(r.status);return r.arrayBuffer();})]);
for(const p of manifest.parts){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(new Float32Array(buffer,p.positionOffset,p.vertexCount*3),3));g.setIndex(new THREE.BufferAttribute(new Uint32Array(buffer,p.indexOffset,p.indexCount),1));g.computeVertexNormals();const material=new THREE.MeshStandardMaterial({color:new THREE.Color(...p.color.map(v=>v/255)).convertSRGBToLinear(),roughness:.72,metalness:p.name.includes('REFERENCE')?.25:.08,flatShading:true});const m=new THREE.Mesh(g,material);m.userData={...p,explode:offset(p)};scene.add(m);meshes.push(m);const o=document.createElement('option');o.value=p.name;o.textContent=pretty(p.name);$('part').append(o);}
// Arrows indicate direction only; these are not a CFD result.
for(const x of [84,270]){air.add(new THREE.ArrowHelper(new THREE.Vector3(0,Math.cos(Math.PI/12),Math.sin(Math.PI/12)),new THREE.Vector3(x,110,76),75,0x79decd,12,7));air.add(new THREE.ArrowHelper(new THREE.Vector3(0,1,0),new THREE.Vector3(x,-82,128),55,0x80c8ff,10,6));air.add(new THREE.ArrowHelper(new THREE.Vector3(0,0,-1),new THREE.Vector3(x,0,72),32,0xf3b76d,8,5));}
$('loading').hidden=true;window.deskDockReady=true;update();view('home');
}catch(e){$('loading').textContent='Could not load the CAD model. Reload this page or open the CAD & notes link.';console.error(e);}
for(const id of ['explode','motion'])$(id).addEventListener('input',()=>{stop();$(id==='explode'?'motion':'explode').value=0;update();});
for(const id of ['laptop','cover','fans','air'])$(id).addEventListener('change',update);
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{if(b.dataset.view==='plug'){$('cover').checked=false;update();}view(b.dataset.view);});
$('part').onchange=()=>select(meshes.find(m=>m.userData.name===$('part').value));
$('reset').onclick=()=>{stop();$('explode').value=$('motion').value=0;for(const id of ['laptop','cover','fans'])$(id).checked=true;$('air').checked=false;select(null);$('part').value='';$('detail').textContent='Choose a component to inspect it.';update();view('home');};
$('play').onclick=()=>{if(playing){stop();return;}playing=true;start=performance.now();$('explode').value=0;$('laptop').checked=true;$('play').textContent='Ⅱ Pause motion';};
let down;canvas.addEventListener('pointerdown',e=>down=[e.clientX,e.clientY]);canvas.addEventListener('pointerup',e=>{if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>5)return;const r=canvas.getBoundingClientRect(),ray=new THREE.Raycaster();ray.setFromCamera(new THREE.Vector2((e.clientX-r.left)/r.width*2-1,1-(e.clientY-r.top)/r.height*2),camera);const hit=ray.intersectObjects(meshes.filter(m=>m.visible))[0];if(hit)select(hit.object);});
new ResizeObserver(()=>{const r=canvas.parentElement.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();}).observe(canvas.parentElement);
function frame(now){requestAnimationFrame(frame);if(playing){const q=((now-start)/1000)%10;const t=q<4?q/4:q<5?1:q<9?1-(q-5)/4:0;$('motion').value=t*100;update();}controls.update();renderer.render(scene,camera);}requestAnimationFrame(frame);
window.deskDockState=()=>({parts:meshes.length,visible:meshes.filter(m=>m.visible).length,explosion:+$('explode').value,motion:+$('motion').value,playing,positions:meshes.filter(m=>moving(m.userData.name)).map(m=>m.position.toArray())});
