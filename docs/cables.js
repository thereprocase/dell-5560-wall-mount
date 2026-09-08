import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { STLLoader } from './vendor/STLLoader.js';

const $ = id => document.getElementById(id);
const parts = [], wires = [];
let renderer, scene, camera, controls;
const smooth = x => { x = Math.max(0, Math.min(1, x)); return x * x * (3 - 2 * x); };
const isVisible = p => (!$('cable-right').checked || p.key.includes('right')) && (!p.optional || $('cable-retainers').checked);
function pose(p, progress) {
  if (p.kind === 'pin') {
    const out = 24 * smooth(progress / .15), up = 20 * smooth((progress - .15) / .1);
    return new THREE.Vector3(0, (out - up) / Math.SQRT2, (out + up) / Math.SQRT2);
  }
  const distance = p.kind === 'cover' ? 35 * smooth((progress - .25) / .75) : 0;
  return new THREE.Vector3(0, distance / Math.SQRT2, distance / Math.SQRT2);
}
function update() {
  const value = Number($('cable-travel').value) / 100;
  const phase = value === 0 ? 'Installed' : value < .25 ? 'Remove cover pins' : value < 1 ? 'Withdraw covers' : 'Covers removed';
  $('cable-phase').textContent = phase;
  $('cable-value').textContent = Math.round(value * 100) + '%';
  $('cable-travel').setAttribute('aria-valuetext', Math.round(value * 100) + '% — ' + phase);
  for (const p of parts) {
    p.group.visible = isVisible(p); p.group.position.copy(pose(p, value));
    p.material.transparent = p.kind === 'arm' && $('cable-ghost').checked;
    p.material.opacity = p.material.transparent ? .18 : 1; p.material.depthWrite = !p.material.transparent;
    p.edges.visible = $('cable-edges').checked;
  }
  for (const w of wires) w.visible = !$('cable-right').checked || w.userData.side === 'right';
  $('cable-count').textContent = parts.filter(isVisible).length + ' mount parts · reference cable in red';
}
function fit() {
  const bounds = new THREE.Box3();
  for (const p of parts.filter(isVisible)) {
    bounds.union(p.geometry.boundingBox.clone());
    bounds.union(p.geometry.boundingBox.clone().translate(pose(p, 1)));
  }
  const center = bounds.getCenter(new THREE.Vector3());
  const radius = bounds.getSize(new THREE.Vector3()).length() / 2;
  const vertical = THREE.MathUtils.degToRad(camera.fov / 2);
  const angle = Math.min(vertical, Math.atan(Math.tan(vertical) * camera.aspect));
  const distance = radius / Math.sin(angle) * 1.07;
  camera.position.copy(center).addScaledVector(new THREE.Vector3(1.1, 1.65, .9).normalize(), distance);
  camera.near = .1; camera.far = 5000; camera.updateProjectionMatrix();
  controls.target.copy(center); controls.update();
}
async function init() {
  const canvas = $('cable-canvas');
  renderer = new THREE.WebGLRenderer({canvas, antialias:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.setClearColor(0x182a31);
  scene = new THREE.Scene(); camera = new THREE.PerspectiveCamera(35,1,.1,5000); camera.up.set(0,0,1);
  controls = new OrbitControls(camera,canvas); controls.enableDamping = true; controls.minDistance = 25; controls.maxDistance = 3500;
  scene.add(new THREE.HemisphereLight(0xeaf8ff,0x16343c,2.8));
  const light = new THREE.DirectionalLight(0xffffff,3); light.position.set(250,400,600); scene.add(light);
  const fill = new THREE.DirectionalLight(0x9cced5,1.5); fill.position.set(-300,-100,200); scene.add(fill);
  const read = async url => {const r=await fetch(url);if(!r.ok)throw Error('Model file unavailable');return r.json();};
  const [base,added,cables] = await Promise.all([read('models/manifest.json'),read('models/retainers/manifest.json?v=h-r1'),read('models/cables/manifest.json?v=h-c1')]);
  const replacements = new Map(cables.parts.map(p=>[p.id,p]));
  const specs = base.map(p=>{
    const replacement = replacements.get(p.key);
    return {key:p.key,kind:replacement?.type || (p.key.includes('cradle')?'arm':p.key.includes('push_pin')?'pin':'base'),
      replacement:Boolean(replacement),path:replacement?'models/cables/'+replacement.file+'?v=h-c1':'models/after/'+p.key+'.stl?v=rev-h-flow'};
  });
  specs.push(...added.parts.map(p=>({key:p.id,kind:p.type,optional:true,path:'models/retainers/'+p.file+'?v=h-r1'})));
  const loader=new STLLoader();
  const loaded=await Promise.all(specs.map(async p=>({...p,geometry:await loader.loadAsync(p.path)})));
  for(const p of loaded){
    p.geometry.computeVertexNormals();p.geometry.computeBoundingBox();
    const color=p.kind==='cover'?0xf59936:p.kind==='tray'?0x31a494:p.kind==='pin'?0xbdd062:p.kind==='arm'?0x637986:p.optional?0x7d9395:0x237b85;
    p.material=new THREE.MeshStandardMaterial({color,roughness:.88,flatShading:true});
    p.edges=new THREE.LineSegments(new THREE.EdgesGeometry(p.geometry,25),new THREE.LineBasicMaterial({color:0x0b252b,transparent:true,opacity:.6}));
    p.group=new THREE.Group();p.group.add(new THREE.Mesh(p.geometry,p.material),p.edges);scene.add(p.group);parts.push(p);
  }
  for(const sign of [-1,1]){
    const wire=new THREE.Mesh(new THREE.CylinderGeometry(2,2,30,24),new THREE.MeshStandardMaterial({color:0xc33742,roughness:.65}));
    wire.rotation.z=Math.PI/2;
    wire.position.set(sign*137,67+(68.2+12.5)/Math.SQRT2,-84+(68.2-12.5)/Math.SQRT2);
    wire.userData.side=sign===1?'right':'left';scene.add(wire);wires.push(wire);
  }
  function resize(){const w=canvas.clientWidth,h=canvas.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();}
  new ResizeObserver(resize).observe(canvas);resize();update();fit();$('cable-loading').hidden=true;
  $('cable-travel').oninput=update;
  $('cable-right').onchange=$('cable-retainers').onchange=()=>{update();fit();};
  $('cable-ghost').onchange=$('cable-edges').onchange=update;
  $('cable-reset').onclick=()=>{$('cable-travel').value=0;$('cable-right').checked=false;update();fit();};
  $('cable-detail').onclick=()=>{$('cable-right').checked=true;update();controls.target.set(139,124,-48);camera.position.set(234,235,9);controls.update();};
  window.cableReview=()=>({ready:true,visible:parts.filter(isVisible).length,phase:$('cable-phase').textContent,
    replacementIds:parts.filter(p=>p.replacement).map(p=>p.key),positions:Object.fromEntries(parts.map(p=>[p.key,p.group.position.toArray()])),
    wirePositions:wires.map(w=>w.position.toArray()),visibleWireCount:wires.filter(w=>w.visible).length});
  renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera);});
}
init().catch(error=>{$('cable-loading').hidden=true;$('cable-error').hidden=false;$('cable-error').textContent='The interactive model could not load. The native views, guide and downloads below remain available. '+error.message;console.error(error);});
