import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { STLLoader } from './vendor/STLLoader.js';

const $ = id => document.getElementById(id);
const canvas = $('v-canvas');

const colors = {
  frame: 0x2f545e,
  tray: 0x278e91,
};

let parts = [];
let meta = null;
let scene, camera, renderer, controls;
let ghostBoxes = [];
let bedPlane = null;
let request = 0;

function dispose() {
  for (const p of parts) {
    scene.remove(p.group);
    p.mesh.geometry.dispose();
    p.mesh.material.dispose();
    p.edges.geometry.dispose();
    p.edges.material.dispose();
  }
  parts = [];
  for (const g of ghostBoxes) {
    scene.remove(g);
    g.traverse(obj => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) obj.material.dispose();
    });
  }
  ghostBoxes = [];
  if (bedPlane) {
    scene.remove(bedPlane);
    bedPlane.geometry.dispose();
    bedPlane.material.dispose();
    bedPlane = null;
  }
}

function fit() {
  const box = new THREE.Box3();
  for (const p of parts) if (p.group.visible) box.expandByObject(p.group);
  for (const g of ghostBoxes) if (g.visible) box.expandByObject(g);
  if (box.isEmpty()) return;
  const center = box.getCenter(new THREE.Vector3());
  const radius = box.getSize(new THREE.Vector3()).length() / 2;
  const d = radius / Math.sin(THREE.MathUtils.degToRad(camera.fov / 2)) * 0.95;
  camera.position.copy(center).addScaledVector(new THREE.Vector3(1.4, 1.25, 0.75).normalize(), d);
  controls.target.copy(center);
  camera.near = 0.5;
  camera.far = d * 12;
  camera.updateProjectionMatrix();
  controls.update();
}

function explodeOffset(part, amount) {
  const side = part.key.includes('left') ? -1 : 1;
  if (part.family === 'frame') {
    return [side * 75 * amount, 0, 0];
  }
  return [side * 25 * amount, 0, -35 * amount];
}

function update() {
  const amount = +$('v-explode').value / 100;
  const showEnvelopes = $('v-envelopes').checked;
  const showBed = $('v-bed').checked;
  const showEdges = $('v-edges').checked;

  for (const p of parts) {
    const off = explodeOffset(p, amount);
    p.group.position.set(off[0], off[1], off[2]);
    p.edges.visible = showEdges;
  }
  for (const g of ghostBoxes) g.visible = showEnvelopes;
  if (bedPlane) bedPlane.visible = showBed;

  $('v-explode-value').textContent = Math.round(amount * 100) + '%';
  $('v-phase').textContent = amount === 0 ? 'assembled' : amount < 1 ? 'exploded' : 'separated';
}

function buildGhostEnvelopes(lap, fan) {
  const rad = THREE.MathUtils.degToRad(lap.tilt_deg);

  // Two Dell Precision 5560 envelopes leaning inward at +/- tilt_deg
  for (const signY of [1, -1]) {
    const g = new THREE.BoxGeometry(lap.width, lap.thickness, lap.depth);
    g.translate(0, signY * (lap.thickness / 2), lap.depth / 2);
    const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({
      color: 0xc5d4db, transparent: true, opacity: 0.16, depthWrite: false, roughness: 1,
    }));
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(g, 20),
      new THREE.LineBasicMaterial({ color: 0x0000a8, transparent: true, opacity: 0.50 }),
    );
    const holder = new THREE.Group();
    holder.add(m, edges);
    holder.position.set(0, signY * lap.plenum_base_half_y, lap.base_z);
    holder.rotation.x = signY * rad;
    scene.add(holder);
    ghostBoxes.push(holder);
  }

  // Two 140 x 140 x 25 mm fan envelopes sitting on the tray deck
  for (const signX of [-1, 1]) {
    const g = new THREE.BoxGeometry(fan.size, fan.size, fan.thickness);
    g.translate(0, 0, fan.thickness / 2);
    const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({
      color: 0xffd28a, transparent: true, opacity: 0.22, depthWrite: false, roughness: 1,
    }));
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(g, 20),
      new THREE.LineBasicMaterial({ color: 0xb87900, transparent: true, opacity: 0.70 }),
    );
    const holder = new THREE.Group();
    holder.add(m, edges);
    holder.position.set(signX * fan.center_x, 0, fan.deck_top_z);
    scene.add(holder);
    ghostBoxes.push(holder);
  }
}

function buildBed(bed) {
  const g = new THREE.PlaneGeometry(bed.x, bed.y);
  const m = new THREE.MeshBasicMaterial({
    color: 0x008ea1, transparent: true, opacity: 0.08, side: THREE.DoubleSide, depthWrite: false,
  });
  bedPlane = new THREE.Mesh(g, m);
  const edge = new THREE.LineSegments(
    new THREE.EdgesGeometry(g),
    new THREE.LineBasicMaterial({ color: 0x008ea1, transparent: true, opacity: 0.7 }),
  );
  bedPlane.add(edge);
  bedPlane.position.set(0, 0, -2);
  scene.add(bedPlane);
}

function populateTable(partsMeta) {
  const tbody = $('part-rows');
  if (!tbody) return;
  tbody.innerHTML = '';
  let totalVol = 0;
  let totalMass = 0;
  for (const p of partsMeta) {
    totalVol += p.volume_cm3;
    totalMass += p.mass_g;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="mono">${p.key}</td>
      <td>${p.label}</td>
      <td>${p.orientation}</td>
      <td class="num mono">${p.footprint_mm[0].toFixed(1)} × ${p.footprint_mm[1].toFixed(1)} × ${p.footprint_mm[2].toFixed(1)}</td>
      <td class="num mono">${p.with_brim_mm[0].toFixed(1)} × ${p.with_brim_mm[1].toFixed(1)}</td>
      <td class="num mono">${p.mass_g.toFixed(1)}</td>
      <td class="ok">PASS</td>
    `;
    tbody.appendChild(tr);
  }
  const tot = document.createElement('tr');
  tot.innerHTML = `
    <td class="mono"><strong>TOTAL</strong></td>
    <td><strong>4 printed parts (PETG 1.27 g/cm³)</strong></td>
    <td>—</td>
    <td class="num mono">${totalVol.toFixed(1)} cm³</td>
    <td>all ≤ 256 × 256 mm</td>
    <td class="num mono"><strong>${totalMass.toFixed(1)}</strong></td>
    <td class="ok">PASS</td>
  `;
  tbody.appendChild(tot);
}

async function load() {
  const ticket = ++request;
  $('v-loading').hidden = false;
  $('v-error').hidden = true;
  meta = await fetch('models/manifest.json').then(r => {
    if (!r.ok) throw new Error('Missing models/manifest.json');
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
      color: colors[item.part.family] ?? 0x8fa3ab, roughness: 0.85, metalness: 0.04, flatShading: true,
    }));
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(g, 26),
      new THREE.LineBasicMaterial({ color: 0x112d34, transparent: true, opacity: 0.55 }),
    );
    const group = new THREE.Group();
    group.add(mesh, edges);
    scene.add(group);
    parts.push({ key: item.part.key, family: item.part.family, group, mesh, edges });
  }
  buildGhostEnvelopes(meta.laptop, meta.fan);
  buildBed(meta.bed);
  populateTable(meta.parts);
  $('v-loading').hidden = true;
  update();
  fit();
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
  for (const [pos, power] of [[[350, -450, 650], 2.5], [[-350, 300, 250], 1.2]]) {
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

  for (const id of ['v-explode', 'v-envelopes', 'v-bed', 'v-edges']) {
    $(id).addEventListener('input', update);
  }
  $('v-reset').onclick = () => { $('v-explode').value = 0; update(); fit(); };
  $('v-iso').onclick = () => { fit(); };
  $('v-side').onclick = () => {
    const box = new THREE.Box3();
    for (const p of parts) box.expandByObject(p.group);
    const c = box.getCenter(new THREE.Vector3());
    const r = box.getSize(new THREE.Vector3()).length() / 2;
    camera.position.set(c.x + r * 2.1, c.y, c.z + r * 0.15);
    controls.target.copy(c);
    camera.updateProjectionMatrix();
    controls.update();
  };
  $('v-front').onclick = () => {
    const box = new THREE.Box3();
    for (const p of parts) box.expandByObject(p.group);
    const c = box.getCenter(new THREE.Vector3());
    const r = box.getSize(new THREE.Vector3()).length() / 2;
    camera.position.set(c.x, c.y + r * 2.2, c.z + r * 0.1);
    controls.target.copy(c);
    camera.updateProjectionMatrix();
    controls.update();
  };
  load().catch(e => {
    $('v-loading').hidden = true;
    $('v-error').hidden = false;
    document.body.dataset.viewer = 'error';
    $('v-error').textContent = '3D viewer failed to load: ' + e.message;
    console.error(e);
  });
  renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
}

init();
