import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { STLLoader } from './vendor/STLLoader.js';
const $=id=>document.getElementById(id), canvas=$('m1-canvas');
const family=k=>k.endsWith('_arm')?'arm':k.includes('fan_cage')?'cage':k.includes('fan_cap')?'cap':k.endsWith('_dam')?'dam':k.endsWith('_key')?'key':'pin';
const isDam=k=>k.includes('_dam');
let parts=[],metadata,camera,controls,scene,renderer,envelope,request=0;
const colors={arm:0x546872,cage:0x278e91,cap:0x54a8a2,dam:0x65a992,key:0xd9ad58,pin:0xd9ad58};
function dispose(){for(const p of parts){scene.remove(p.group);p.mesh.geometry.dispose();p.mesh.material.dispose();p.edges.geometry.dispose();p.edges.material.dispose();}parts=[];if(envelope){scene.remove(envelope);envelope.geometry.dispose();envelope.material.dispose();envelope=null;}}
function fit(){const box=new THREE.Box3();for(const p of parts)if(p.group.visible)box.expandByObject(p.group);if(box.isEmpty())return;const center=box.getCenter(new THREE.Vector3()),radius=box.getSize(new THREE.Vector3()).length()/2,d=radius/Math.sin(THREE.MathUtils.degToRad(camera.fov/2))*1.06;camera.position.copy(center).addScaledVector(new THREE.Vector3(1.1,1.7,1).normalize(),d);controls.target.copy(center);camera.near=.1;camera.far=d*10;camera.updateProjectionMatrix();controls.update();}
// Each stage is a pure function of slider position, so moving left retraces
// the same sequence: seat parts, insert pins/keys, then engage the lock pins.
function assemblyOffset(part, amount) {
  const locks = THREE.MathUtils.smoothstep(amount, 0, .25);
  const pins = THREE.MathUtils.smoothstep(amount, .25, .5);
  const separate = THREE.MathUtils.smoothstep(amount, .5, 1);
  const side = part.key.includes('left') ? -1 : 1;
  const fanAxis = Math.SQRT1_2;
  const capShift = [side * 18, 25 + 60 * fanAxis, -30 + 60 * fanAxis];
  let withdrawn = [0, 0, 0], spread;
  if (part.key.endsWith('_keeper')) {
    // Vertical keepers must clear both tongues before a two-rung key moves.
    withdrawn = [0, 0, 40 * locks];
    spread = [side * 70, 0, isDam(part.key) ? 80 : 20];
  } else if (part.family === 'key') {
    withdrawn = [side * 35 * pins, 0, 0];
    spread = [side * 40, 0, isDam(part.key) ? 55 : -30];
  } else if (part.family === 'pin') {
    // Cap pins withdraw along fan-local +Y, tilted 45 degrees about X.
    withdrawn = [0, 30 * fanAxis * pins, 30 * fanAxis * pins];
    spread = capShift;
  } else {
    spread = {
      arm: [side * 40, 0, 0],
      cage: [side * 18, 25, -30],
      cap: capShift,
      dam: [side * 18, 0, 55],
    }[part.family];
  }
  return spread.map((value, axis) => withdrawn[axis] + value * separate);
}
function update() {
  const index = +$('m1-index').value, amount = +$('m1-explode').value / 100;
  const dam = $('m1-dam').checked, percent = Math.round(amount * 100);
  const phase = amount === 0 ? 'Installed' : amount <= .25 ? 'Lock pins'
    : amount <= .5 ? 'Other pins and keys' : amount < 1 ? 'Separate parts' : 'Uninstalled';
  $('m1-index-value').textContent = index + ' / 8';
  $('m1-explode-value').textContent = percent + '%';
  $('m1-sequence-phase').textContent = phase;
  $('m1-explode').setAttribute('aria-valuetext', percent + '% — ' + phase);
  let count = 0;
  for (const part of parts) {
    const shift = assemblyOffset(part, amount);
    shift[2] += isDam(part.key) ? (index - 8) * 12 : 0;
    part.group.position.set(...shift);
    part.group.visible = dam || !isDam(part.key);
    part.edges.visible = $('m1-edges').checked;
    if (part.group.visible) count++;
  }
  if (envelope) envelope.visible = $('m1-laptop').checked;
  $('m1-count').textContent = count + ' parts · ' + phase.toLowerCase();
}
async function loadPreset(name){const ticket=++request;$('m1-loading').hidden=false;$('m1-error').hidden=true;const preset=metadata.presets[name];const loader=new STLLoader();let loaded=[];try{loaded=await Promise.all(preset.parts.map(async p=>({key:p.key,geometry:await loader.loadAsync('models/minimalist/'+name+'/'+p.key+'.stl?v=m1.1')})));if(ticket!==request){loaded.forEach(p=>p.geometry.dispose());return;}dispose();for(const item of loaded){const f=family(item.key),g=item.geometry;g.computeVertexNormals();const mesh=new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:colors[f],roughness:.88,flatShading:true}));const edges=new THREE.LineSegments(new THREE.EdgesGeometry(g,25),new THREE.LineBasicMaterial({color:0x112d34,transparent:true,opacity:.6}));const group=new THREE.Group();group.add(mesh,edges);scene.add(group);parts.push({key:item.key,family:f,group,mesh,edges});}envelope=new THREE.Mesh(new THREE.BoxGeometry(preset.width,preset.thickness,preset.depth),new THREE.MeshStandardMaterial({color:0xc5d4db,transparent:true,opacity:.18,depthWrite:false}));envelope.position.set(0,40+preset.thickness/2,2+preset.depth/2);scene.add(envelope);$('m1-label').textContent=preset.label+' · '+preset.width+' × '+preset.depth+' × '+preset.thickness+' mm';$('m1-download').href='downloads/Minimalist_M1_'+name+'.zip?v=m1.1';update();fit();$('m1-loading').hidden=true;window.minimalistReady=true;window.minimalistPreset=name;}catch(e){if(ticket===request){$('m1-loading').hidden=true;$('m1-error').hidden=false;$('m1-error').textContent='The model could not load. Print sets and the illustrated guide remain available. '+e.message;}throw e;}}
async function init(){renderer=new THREE.WebGLRenderer({canvas,antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor(0x182a31);scene=new THREE.Scene();camera=new THREE.PerspectiveCamera(35,1,.1,5000);camera.up.set(0,0,1);controls=new OrbitControls(camera,canvas);controls.enableDamping=true;scene.add(new THREE.HemisphereLight(0xf0ffff,0x24434b,2.8));for(const [pos,power] of [[[250,400,600],3],[[-300,-100,200],1.5]]){const l=new THREE.DirectionalLight(0xffffff,power);l.position.set(...pos);scene.add(l);}new ResizeObserver(()=>{const w=canvas.clientWidth,h=canvas.clientHeight;if(!w||!h)return;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();}).observe(canvas);metadata=await fetch('models/minimalist/manifest.json?v=m1.1').then(r=>{if(!r.ok)throw Error('Missing model manifest');return r.json();});$('m1-preset').onchange=()=>loadPreset($('m1-preset').value).catch(console.error);for(const id of ['m1-index','m1-explode','m1-dam','m1-laptop','m1-edges'])$(id).addEventListener('input',update);$('m1-reset').onclick=()=>{$('m1-explode').value=0;update();fit();};await loadPreset($('m1-preset').value);renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera);});window.minimalistState=()=>({preset:window.minimalistPreset,index:+$('m1-index').value,visibleParts:parts.filter(p=>p.group.visible).length,damZ:parts.find(p=>p.family==='dam')?.group.position.z,assemblyPercent:+$('m1-explode').value,partPositions:Object.fromEntries(parts.map(p=>[p.key,p.group.position.toArray()]))});}
init().catch(e=>{$('m1-loading').hidden=true;$('m1-error').hidden=false;$('m1-error').textContent='The interactive view is unavailable. Use the downloads and illustrated guide. '+e.message;console.error(e);});
