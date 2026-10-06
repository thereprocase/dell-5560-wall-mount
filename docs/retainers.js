import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { STLLoader } from './vendor/STLLoader.js';

const $ = id => document.getElementById(id);
const canvas = $('retainer-canvas');
const parts = [];
let renderer, scene, camera, controls;
const smooth = t => { t = Math.max(0, Math.min(1, t)); return t * t * (3 - 2 * t); };
const isVisible = p => !$('retainer-right').checked || p.key.includes('right');
function pose(p, value) {
  const side = p.key.includes('left') ? -1 : 1;
  if (p.kind === 'keeper') return new THREE.Vector3(0, 0, -16 * smooth(value / .4));
  if (p.kind === 'bar') return new THREE.Vector3(side * 30 * smooth((value - .4) / .6), 0, 0);
  return new THREE.Vector3();
}
function update() {
  const value = Number($('retainer-travel').value) / 100;
  const phase = value === 0 ? 'Installed' : value < .4 ? 'Remove keepers' : value < 1 ? 'Withdraw side bars' : 'Retainers removed';
  $('retainer-phase').textContent = phase;
  $('retainer-value').textContent = Math.round(value * 100) + '%';
  $('retainer-travel').setAttribute('aria-valuetext', Math.round(value * 100) + '% — ' + phase);
  for (const p of parts) {
    p.group.visible = isVisible(p);
    p.group.position.copy(pose(p, value));
    p.material.transparent = p.kind === 'arm' && $('retainer-ghost').checked;
    p.material.opacity = p.material.transparent ? .18 : 1;
    p.material.depthWrite = !p.material.transparent;
    p.edges.visible = $('retainer-edges').checked;
  }
  $('retainer-count').textContent = parts.filter(isVisible).length + ' installed parts';
}
function fit() {
  const bounds = new THREE.Box3();
  for (const p of parts.filter(isVisible)) {
    const b = p.geometry.boundingBox;
    bounds.union(b.clone().translate(pose(p, 0)));
    bounds.union(b.clone().translate(pose(p, 1)));
  }
  const center = bounds.getCenter(new THREE.Vector3());
  const radius = bounds.getSize(new THREE.Vector3()).length() / 2;
  const distance = radius / Math.sin(THREE.MathUtils.degToRad(camera.fov / 2)) * 1.12;
  camera.position.copy(center).addScaledVector(new THREE.Vector3(1.1, 1.65, .9).normalize(), distance);
  camera.near = .1; camera.far = 5000; camera.updateProjectionMatrix();
  controls.target.copy(center); controls.update();
}
async function init() {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.setClearColor(0x182a31);
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(35, 1, .1, 5000); camera.up.set(0, 0, 1);
  controls = new OrbitControls(camera, canvas); controls.enableDamping = true; controls.minDistance = 25; controls.maxDistance = 2500;
  scene.add(new THREE.HemisphereLight(0xeaf8ff, 0x16343c, 2.8));
  const light = new THREE.DirectionalLight(0xffffff, 3); light.position.set(250, 400, 600); scene.add(light);
  const fill = new THREE.DirectionalLight(0x9cced5, 1.5); fill.position.set(-300, -100, 200); scene.add(fill);
  const read = async url => { const r = await fetch(url); if (!r.ok) throw Error('Model file unavailable'); return r.json(); };
  const [base, added] = await Promise.all([read('models/manifest.json'), read('models/retainers/manifest.json?v=h-r1')]);
  const specs = [
    ...base.map(p => ({ key: p.key, label: p.label, path: 'models/after/' + p.key + '.stl?v=rev-h-flow', kind: p.key.includes('cradle') ? 'arm' : 'base' })),
    ...added.parts.map(p => ({ key: p.id, label: p.id.replaceAll('_', ' '), path: 'models/retainers/' + p.file + '?v=h-r1', kind: p.type }))
  ];
  const loader = new STLLoader();
  const loaded = await Promise.all(specs.map(async p => ({ ...p, geometry: await loader.loadAsync(p.path) })));
  for (const p of loaded) {
    p.geometry.computeVertexNormals(); p.geometry.computeBoundingBox();
    const color = p.kind === 'bar' ? 0xf79129 : p.kind === 'keeper' ? 0x59cc59 : p.kind === 'arm' ? 0x637986 : 0x188c91;
    p.material = new THREE.MeshStandardMaterial({ color, roughness: .88, flatShading: true });
    p.mesh = new THREE.Mesh(p.geometry, p.material);
    p.edges = new THREE.LineSegments(new THREE.EdgesGeometry(p.geometry, 25), new THREE.LineBasicMaterial({ color: 0x0b252b, transparent: true, opacity: .6 }));
    p.group = new THREE.Group(); p.group.add(p.mesh, p.edges); scene.add(p.group); parts.push(p);
  }
  function resize() {
    const width = canvas.clientWidth, height = canvas.clientHeight;
    renderer.setSize(width, height, false); camera.aspect = width / height; camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(canvas); resize(); update(); fit();
  $('retainer-loading').hidden = true;
  $('retainer-travel').oninput = update;
  $('retainer-right').onchange = () => { update(); fit(); };
  $('retainer-ghost').onchange = update; $('retainer-edges').onchange = update;
  $('retainer-reset').onclick = () => { $('retainer-travel').value = 0; update(); fit(); };
  $('retainer-detail').onclick = () => {
    $('retainer-right').checked = true; update();
    controls.target.set(178, 43, -22); camera.position.set(98, 140, 40); controls.update();
  };
  window.retainerReview = () => ({ ready: true, visible: parts.filter(isVisible).length,
    phase: $('retainer-phase').textContent,
    positions: Object.fromEntries(parts.map(p => [p.key, p.group.position.toArray()])) });
  renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
}
init().catch(error => {
  $('retainer-loading').hidden = true; $('retainer-error').hidden = false;
  $('retainer-error').textContent = 'The interactive model could not load. The native views, guide and downloads below are still available. ' + error.message;
  console.error(error);
});
