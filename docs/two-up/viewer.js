import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { STLLoader } from './vendor/STLLoader.js';

const $ = id => document.getElementById(id);
const canvas = $('v-canvas');

const colors = {
  arm: 0x546872, cage: 0x278e91, cap: 0x54a8a2,
  cheek: 0x8fa3ab, dam: 0x65a992, key: 0xd9ad58, pin: 0xb87900,
};

let parts = [], meta, scene, camera, renderer, controls, envelope, laptopBoxes = [];
let bedPlane = null, request = 0;

function dispose() {
  for (const p of parts) {
    scene.remove(p.group);
    p.mesh.geometry.dispose();
    p.mesh.material.dispose();
    p.edges.geometry.dispose();
    p.edges.material.dispose();
  }
  parts = [];
  for (const b of laptopBoxes) { scene.remove(b); b.geometry.dispose(); b.material.dispose(); }
  laptopBoxes = [];
  if (envelope) { scene.remove(envelope); envelope.geometry.dispose(); envelope.material.dispose(); envelope = null; }
  if (bedPlane) { scene.remove(bedPlane); bedPlane.geometry.dispose(); bedPlane.material.dispose(); bedPlane = null; }
}

function fit() {
  const box = new THREE.Box3();
  for (const p of parts) if (p.group.visible) box.expandByObject(p.group);
  for (const b of laptopBoxes) if (b.visible) box.expandByObject(b);
  if (box.isEmpty()) return;
  const center = box.getCenter(new THREE.Vector3());
  const radius = box.getSize(new THREE.Vector3()).length() / 2;
  const d = radius / Math.sin(THREE.MathUtils.degToRad(camera.fov / 2)) * 0.94;
  // Y grows away from the wall, so the viewer sits at +Y looking back at the mount.
  camera.position.copy(center).addScaledVector(new THREE.Vector3(0.85, 1.65, 0.42).normalize(), d);
  controls.target.copy(center);
  camera.near = 0.5;
  camera.far = d * 12;
  camera.updateProjectionMatrix();
  controls.update();
}

// Explode along each part's own outward direction. Arms and cheeks move sideways,
// dams and cages lift forward off the wall, hardware drops down and out so the
// rungs it engages stay legible.
function explodeOffset(part, amount) {
  const side = part.key.includes('left') ? -1 : 1;
  const tier = part.key.includes('tier2') || part.key.includes('upper') ? 1 : 0;
  const base = {
    arm: [side * 55, 0, 0],
    cheek: [side * 90, 10, 0],
    dam: [side * 30, 45, 0],
    cage: [side * 20, 70, 0],
    cap: [side * 20, 110, 0],
    key: [side * 40, 0, 18],
    pin: [side * 70, 0, 45],
  }[part.family] || [0, 0, 0];
  return base.map((v, i) => v * amount + (i === 2 ? tier * 26 * amount : 0));
}

function update() {
  const amount = +$('v-explode').value / 100;
  const showHardware = $('v-hardware').checked;
  const showLaptop = $('v-laptop').checked;
  const showBed = $('v-bed').checked;
  const showEdges = $('v-edges').checked;

  let visible = 0;
  for (const p of parts) {
    const isHardware = p.family === 'key' || p.family === 'pin';
    p.group.visible = showHardware || !isHardware;
    const off = explodeOffset(p, amount);
    p.group.position.set(p.orig[0] + off[0], p.orig[1] + off[1], p.orig[2] + off[2]);
    p.edges.visible = showEdges;
    if (p.group.visible) visible++;
  }
  for (const b of laptopBoxes) b.visible = showLaptop;
  if (bedPlane) bedPlane.visible = showBed;

  const percent = Math.round(amount * 100);
  $('v-explode-value').textContent = percent + '%';
  $('v-count').textContent = visible + ' parts';
  $('v-phase').textContent = amount === 0 ? 'installed' : amount < 1 ? 'exploded' : 'separated';
}

function buildLaptops(laptop) {
  const rad = THREE.MathUtils.degToRad(laptop.tilt_deg);
  const rearFace = 38.0; // wallGap 40 mm minus the 2 mm compliant pad
  for (const baseZ of [laptop.lower_base_z, laptop.upper_base_z]) {
    // The case stands nearly upright and leans back 15 degrees: depth runs up
    // Z, thickness runs out along Y, width stays on X.
    const g = new THREE.BoxGeometry(laptop.width, laptop.thickness, laptop.depth);
    // Pivot on the lower rear edge so the hinge tips forward, away from the wall.
    g.translate(0, laptop.thickness / 2, laptop.depth / 2);
    const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({
      color: 0xc5d4db, transparent: true, opacity: 0.16, depthWrite: false, roughness: 1,
    }));
    const holder = new THREE.Group();
    holder.add(m);
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(g, 20),
      new THREE.LineBasicMaterial({ color: 0x0000a8, transparent: true, opacity: 0.45 }));
    holder.add(edges);
    holder.position.set(0, rearFace, baseZ);
    holder.rotation.x = -rad;
    scene.add(holder);
    laptopBoxes.push(holder);
  }
}

function buildBed(bed) {
  const g = new THREE.PlaneGeometry(bed.x, bed.y);
  const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({
    color: 0x008ea1, transparent: true, opacity: 0.08, side: THREE.DoubleSide, depthWrite: false,
  }));
  bedPlane = new THREE.Mesh(g, m);
  const edge = new THREE.LineSegments(new THREE.EdgesGeometry(g),
    new THREE.LineBasicMaterial({ color: 0x008ea1, transparent: true, opacity: 0.7 }));
  bedPlane.add(edge);
  bedPlane.position.set(0, 0, meta.envelope.min[2] - 6);
  bedPlane.rotation.x = -Math.PI / 2;
  scene.add(bedPlane);
}

async function load() {
  const ticket = ++request;
  $('v-loading').hidden = false;
  $('v-error').hidden = true;
  meta = await fetch('models/manifest.json').then(r => {
    if (!r.ok) throw new Error('Missing model manifest');
    return r.json();
  });
  const loader = new STLLoader();
  const loaded = await Promise.all(meta.parts.map(async p => ({
    part: p,
    geometry: await loader.loadAsync('models/' + p.key + '.stl'),
  })));
  if (ticket !== request) { loaded.forEach(l => l.geometry.dispose()); return; }

  dispose();
  for (const item of loaded) {
    const g = item.geometry;
    g.computeVertexNormals();
    const mesh = new THREE.Mesh(g, new THREE.MeshStandardMaterial({
      color: colors[item.part.family] ?? 0x8fa3ab, roughness: 0.9, metalness: 0.02, flatShading: true,
    }));
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(g, 28),
      new THREE.LineBasicMaterial({ color: 0x112d34, transparent: true, opacity: 0.55 }));
    const group = new THREE.Group();
    group.add(mesh, edges);
    // The STLs are exported in the installed assembly position, so the source
    // placement is already correct; keep the origin for the explode slider.
    scene.add(group);
    parts.push({
      key: item.part.key, family: item.part.family, group, mesh, edges,
      orig: [0, 0, 0], mass: item.part.mass_g,
    });
  }
  buildLaptops(meta.laptop);
  buildBed(meta.bed);
  $('v-loading').hidden = true;
  update();
  fit();
  window.twoUpReady = true;
  document.body.dataset.viewer = 'ready';
}

function init() {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setClearColor(0xe8e8e8);
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(34, 1, 0.5, 8000);
  camera.up.set(0, 0, 1);
  controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  scene.add(new THREE.HemisphereLight(0xffffff, 0xb0b8bc, 2.6));
  for (const [pos, power] of [[[300, -500, 700], 2.6], [[-350, 250, 250], 1.1]]) {
    const l = new THREE.DirectionalLight(0xffffff, power);
    l.position.set(...pos);
    scene.add(l);
  }
  new ResizeObserver(() => {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }).observe(canvas);
  for (const id of ['v-explode', 'v-hardware', 'v-laptop', 'v-bed', 'v-edges']) {
    $(id).addEventListener('input', update);
  }
  $('v-reset').onclick = () => { $('v-explode').value = 0; update(); fit(); };
  $('v-iso').onclick = () => { fit(); };
  $('v-side').onclick = () => {
    const box = new THREE.Box3();
    for (const p of parts) if (p.group.visible) box.expandByObject(p.group);
    const c = box.getCenter(new THREE.Vector3());
    const r = box.getSize(new THREE.Vector3()).length() / 2;
    camera.position.set(c.x + r * 1.9, c.y + r * 0.25, c.z + r * 0.1);
    controls.target.copy(c);
    camera.updateProjectionMatrix();
    controls.update();
  };
  $('v-front').onclick = () => {
    const box = new THREE.Box3();
    for (const p of parts) if (p.group.visible) box.expandByObject(p.group);
    const c = box.getCenter(new THREE.Vector3());
    const r = box.getSize(new THREE.Vector3()).length() / 2;
    camera.position.set(c.x, c.y + r * 2.0, c.z + r * 0.05);
    controls.target.copy(c);
    camera.updateProjectionMatrix();
    controls.update();
  };
  load().catch(e => {
    $('v-loading').hidden = true;
    $('v-error').hidden = false;
    document.body.dataset.viewer = 'error';
    $('v-error').textContent = 'The 3D view could not load. The STEP/STL package still downloads. ' + e.message;
    console.error(e);
  });
  renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
}

init();
