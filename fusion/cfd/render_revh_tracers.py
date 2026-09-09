"""Animate projected 2D tracers through the recorded, time-varying CFD slice.

Uses physical velocities and physical time. These are visualization tracers,
not reconstructed 3D particle trajectories or new CFD solution states.
"""
import os
os.environ['VTK_SMP_MAX_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ.setdefault('WINDIR', 'C:/Windows')
os.environ.setdefault('SystemRoot', 'C:/Windows')
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
os.environ.setdefault('USERPROFILE', str(Path(os.environ['LOCALAPPDATA']).parents[1]))
import subprocess
import time
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from PIL import Image
from render_revh_progress import read_plane, cad_sections, choose

FPS = 60
SPEED = 5
PARTICLES = 320
TRAIL = 11
MAX_STEP = 12.5e-6
BASE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Slice:
    """Use original triangle connectivity, including holes, for interpolation."""
    def __init__(self, pts, triangles):
        self.points = pts
        self.triangles = triangles
        xyz = np.column_stack((pts, np.zeros(len(pts))))
        vp = vtk.vtkPoints()
        vp.SetData(numpy_to_vtk(xyz, deep=True))
        cells = vtk.vtkCellArray()
        cells.SetCells(len(triangles), numpy_to_vtkIdTypeArray(
            np.column_stack((np.full(len(triangles), 3), triangles)).astype(np.int64).ravel(), deep=True))
        self.poly = vtk.vtkPolyData()
        self.poly.SetPoints(vp)
        self.poly.SetPolys(cells)
        self.locator = vtk.vtkStaticCellLocator()
        self.locator.SetDataSet(self.poly)
        self.locator.BuildLocator()
        self.a = pts[triangles[:, 0]]
        self.ab = pts[triangles[:, 1]] - self.a
        self.ac = pts[triangles[:, 2]] - self.a
        self.det = self.ab[:, 0] * self.ac[:, 1] - self.ab[:, 1] * self.ac[:, 0]

    def locate(self, positions):
        return np.fromiter((self.locator.FindCell((float(y), float(z), 0.))
                            if np.isfinite(y + z) else -1 for y, z in positions), dtype=np.int64)

    def values(self, positions, field):
        indices = self.locate(positions)
        valid = indices >= 0
        valid[valid] &= np.abs(self.det[indices[valid]]) > 1e-12
        result = np.full((len(positions), field.shape[1]), np.nan)
        ii = indices[valid]
        q = positions[valid] - self.a[ii]
        v = (q[:, 0] * self.ac[ii, 1] - q[:, 1] * self.ac[ii, 0]) / self.det[ii]
        w = (self.ab[ii, 0] * q[:, 1] - self.ab[ii, 1] * q[:, 0]) / self.det[ii]
        weights = np.column_stack((1 - v - w, v, w))
        result[valid] = np.einsum('ij,ijk->ik', weights, field[self.triangles[ii]])
        return result


def rk2_step(positions, velocity_at, dt):
    """Positions are mm; input velocity is m/s and dt is seconds."""
    v0 = velocity_at(positions, 0.)
    mid = positions + v0 * (dt * 500.)
    vm = velocity_at(mid, .5)
    return positions + vm * (dt * 1000.)


class Cloud:
    def __init__(self, section, bounds, seed):
        self.section, self.bounds = section, np.array(bounds)
        self.rng = np.random.default_rng(seed)
        self.positions = np.full((PARTICLES, 2), np.nan)
        self.history = np.full((TRAIL, PARTICLES, 2), np.nan)
        self.age = np.zeros(PARTICLES)
        self.lifetime = self.rng.uniform(.012, .026, PARTICLES)
        self.respawned = 0
        self.travel_mm = 0.
        self.particle_steps = 0
        self.max_displacement_mm = 0.

    def inside(self, positions):
        x0, x1, y0, y1 = self.bounds
        return ((positions[:, 0] > x0) & (positions[:, 0] < x1)
                & (positions[:, 1] > y0) & (positions[:, 1] < y1))

    def seed(self, dead):
        count = int(dead.sum())
        if not count:
            return
        x0, x1, y0, y1 = self.bounds
        accepted = []
        while sum(len(a) for a in accepted) < count:
            candidates = self.rng.uniform([x0, y0], [x1, y1], size=(max(128, count * 2), 2))
            accepted.append(candidates[self.section.locate(candidates) >= 0])
        self.positions[dead] = np.concatenate(accepted)[:count]
        self.history[:, dead] = np.nan
        self.age[dead] = 0.
        self.lifetime[dead] = self.rng.uniform(.012, .026, count)
        self.respawned += count

    def step(self, field0, field1, weight, weight_mid, dt):
        self.seed(~np.isfinite(self.positions[:, 0]))
        old = self.positions.copy()
        def velocity_at(positions, fraction):
            blend = weight_mid if fraction else weight
            return self.section.values(positions, field0 * (1 - blend) + field1 * blend)
        new = rk2_step(old, velocity_at, dt)
        valid = np.isfinite(new).all(axis=1) & self.inside(new)
        # Check intermediate positions as well as the endpoint, so particles
        # are discarded at sampled solids instead of jumping across a wall.
        for fraction in (.25, .5, .75, 1.):
            valid &= self.section.locate(old + (new - old) * fraction) >= 0
        self.age += dt
        valid &= self.age < self.lifetime
        distances = np.linalg.norm(new[valid] - old[valid], axis=1)
        self.travel_mm += float(distances.sum())
        self.particle_steps += len(distances)
        self.max_displacement_mm = max(self.max_displacement_mm, float(distances.max(initial=0)))
        self.positions = new
        self.seed(~valid)

    def snapshot(self):
        self.history[:-1] = self.history[1:]
        self.history[-1] = self.positions
        return np.stack((self.history[:-1], self.history[1:]), axis=2).reshape(-1, 2, 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--page', type=Path, required=True)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preview-frames', type=int, default=0)
    args = parser.parse_args()
    if os.name == 'nt':
        import ctypes
        assert ctypes.windll.kernel32.SetPriorityClass(ctypes.c_void_p(-1), subprocess.IDLE_PRIORITY_CLASS)
    args.output.mkdir(parents=True, exist_ok=False)
    report_path = args.page / args.checkpoint / 'progress.json'
    source = json.loads(report_path.read_text(encoding='utf-8'))
    times = np.array(source['physical_times_s'])
    directories = {float(p.name): p for p in (args.case / 'postProcessing/edge_sections').iterdir()
                   if p.is_dir() and not p.name.startswith('.')}
    read_count = 0
    section = None
    layouts = {}
    def load(index):
        nonlocal read_count, section
        path = directories[float(times[index])] / 'right_section.vtp'
        assert sha(path) == source['source_sha256'][str(float(times[index]))]
        pts, tri, fields = read_plane(path)
        signature = hashlib.sha256(pts.tobytes() + tri.tobytes()).hexdigest()
        if section is None:
            section = Slice(pts, tri)
            layouts[signature] = np.arange(len(pts))
        if signature not in layouts:
            # Changing MPI decomposition reorders this same sampled mesh.
            # Accept only exact coordinate and triangle-set equivalence.
            reference_order = np.lexsort((section.points[:, 1], section.points[:, 0]))
            incoming_order = np.lexsort((pts[:, 1], pts[:, 0]))
            assert np.array_equal(pts[incoming_order], section.points[reference_order]), 'Sample coordinates changed'
            incoming_to_reference = np.empty(len(pts), dtype=np.int64)
            incoming_to_reference[incoming_order] = reference_order
            a = np.sort(section.triangles, axis=1)
            b = np.sort(incoming_to_reference[tri], axis=1)
            assert np.array_equal(a[np.lexsort(a.T)], b[np.lexsort(b.T)]), 'Sample connectivity changed'
            permutation = np.empty(len(pts), dtype=np.int64)
            permutation[reference_order] = incoming_order
            layouts[signature] = permutation
        read_count += 1
        return np.column_stack((fields['U'][:, 1:], fields['p'] * 1.2))[layouts[signature]]

    first = load(0)
    second = load(1)
    slowdown = source['playback_slowdown'] / SPEED
    count = int(round((times[-1] - times[0]) * slowdown * FPS)) + 1
    extension = source.get('visual_extension')
    if extension:
        assert abs(extension['video_frame_step_s'] - 1 / (FPS * slowdown)) < 1e-12
        count = extension['base_motion_frames'] + extension['new_frames']
    if args.preview_frames:
        count = min(count, args.preview_frames)
    width, height = 1800, 1100
    plt.rcParams.update({'font.size': 13, 'axes.titlesize': 19, 'axes.labelsize': 12,
                         'figure.facecolor': '#f7f9fa'})
    fig, axes = plt.subplots(1, 2, figsize=(18, 11), dpi=100)
    fig.subplots_adjust(left=.065, right=.945, bottom=.19, top=.81, wspace=.25)
    warm = source['initialization_kind'] == 'steady_solver'
    phase = 'From already flowing air' if warm else 'Startup from still air'
    fig.text(.055, .945, 'REV H  |  FOLLOW THE MOVING AIR', fontsize=26, fontweight='bold', color='#162c36')
    fig.text(.055, .9, f'{phase}  |  Moving tracers + fading trails  |  5x playback', fontsize=18, color='#17686b')
    timestamp = fig.text(.055, .852, '', fontsize=18, color='#162c36', animated=True)
    fig.text(.055, .112, 'Dots follow sampled in-plane velocity at X = +111 mm. Background: static pressure [Pa].', fontsize=16, color='#162c36')
    fig.text(.055, .073, 'Projected 2D visualization: velocity is interpolated between saved samples; out-of-plane motion is omitted.', fontsize=13, color='#536772')
    fig.text(.055, .042, 'Tracers are reseeded at exits, solids or age limits. Provisional CFD; mesh and timestep independence remain unproven.', fontsize=12, color='#536772')
    lines = cad_sections()
    clouds, artists = [], []
    for i, (ax, title, bounds) in enumerate(zip(axes, ['Front lip / duct outlet', 'Hinge lip / discharge'],
                                                [(25, 75, -8, 35), (25, 75, 208, 262)])):
        cloud = Cloud(section, bounds, seed=20260909 + i)
        cloud.seed(np.ones(PARTICLES, dtype=bool))
        clouds.append(cloud)
        triangles = choose(section.points, section.triangles, bounds)
        mesh = ax.tripcolor(section.points[:, 0], section.points[:, 1], triangles, first[:, 2],
                            cmap='RdBu_r', vmin=-12, vmax=12, shading='gouraud', animated=True)
        outline = LineCollection(lines, colors='#172d36', linewidths=1.4, animated=True)
        ax.add_collection(outline)
        alpha = np.repeat(np.linspace(.04, .65, TRAIL - 1), PARTICLES)
        colors = np.tile([.04, .16, .20, 1.], (len(alpha), 1)); colors[:, 3] = alpha
        trails = LineCollection([], colors=colors, linewidths=1.5, animated=True)
        ax.add_collection(trails)
        heads = ax.scatter([], [], s=4, facecolors='black', edgecolors='none', linewidths=0, animated=True)
        ax.set(xlim=bounds[:2], ylim=bounds[2:], aspect='equal', title=title,
               xlabel='Y from wall [mm]', ylabel='Height Z [mm]', facecolor='#cdd5db')
        fig.colorbar(mesh, ax=ax, fraction=.045, pad=.03, shrink=.9, label='Static pressure [Pa]')
        artists.append((mesh, outline, trails, heads))
    fig.canvas.draw()
    background = fig.canvas.copy_from_bbox(fig.bbox)
    video = args.output / 'tracers.mp4'
    command = ['F:/Code/gpu-offload/bin/ffmpeg.exe', '-hide_banner', '-loglevel', 'error',
               '-f', 'rawvideo', '-pixel_format', 'rgba', '-video_size', f'{width}x{height}',
               '-framerate', str(FPS), '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-threads', '2',
               '-preset', 'slow', '-crf', '26', '-pix_fmt', 'yuv420p', '-g', str(FPS),
               '-movflags', '+faststart', str(video)]
    started = time.monotonic()
    physical_time = float(times[0])
    interval = 0
    encoded = 0
    with (args.output / 'encoding.log').open('w') as log:
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
        try:
            for frame in range(count):
                target = min(float(times[-1]), float(times[0] + frame / (FPS * slowdown)))
                if extension and frame >= extension['base_motion_frames'] - 1:
                    target = extension['base_last_time_s'] + (frame - extension['base_motion_frames'] + 1) * extension['video_frame_step_s']
                if frame == count - 1 and not args.preview_frames:
                    target = float(times[-1])
                while physical_time < target - 1e-14:
                    if physical_time >= times[interval + 1] - 1e-14:
                        interval += 1
                        first = second
                        second = load(interval + 1)
                    step = min(MAX_STEP, target - physical_time, times[interval + 1] - physical_time)
                    duration = times[interval + 1] - times[interval]
                    weight = (physical_time - times[interval]) / duration
                    weight_mid = (physical_time + step * .5 - times[interval]) / duration
                    for cloud in clouds:
                        cloud.step(first[:, :2], second[:, :2], weight, weight_mid, step)
                    physical_time += step
                blend = np.clip((physical_time - times[interval]) / (times[interval + 1] - times[interval]), 0, 1)
                pressure = first[:, 2] * (1 - blend) + second[:, 2] * blend
                fig.canvas.restore_region(background)
                timestamp.set_text(f'Simulation time: {physical_time * 1000:.4f} ms  |  {slowdown:.0f}x slower than physical time')
                for ax, cloud, (mesh, outline, trails, heads) in zip(axes, clouds, artists):
                    mesh.set_array(pressure)
                    trails.set_segments(cloud.snapshot())
                    heads.set_offsets(cloud.positions)
                    for artist in (mesh, trails, heads, outline):
                        ax.draw_artist(artist)
                fig.draw_artist(timestamp)
                pixels = memoryview(fig.canvas.buffer_rgba()).tobytes()
                encoder.stdin.write(pixels)
                encoded += 1
                if frame in (0, min(60, count - 1), count - 1):
                    Image.fromarray(np.asarray(fig.canvas.buffer_rgba())).convert('RGB').save(args.output / f'frame-{frame:04d}.png')
                if frame % 60 == 0:
                    print(json.dumps({'frame': frame, 'frames': count, 'physical_time_s': physical_time,
                                      'elapsed_s': time.monotonic() - started}), flush=True)
            if not args.preview_frames:
                for _ in range(6):
                    encoder.stdin.write(pixels)
                    encoded += 1
        finally:
            encoder.stdin.close()
            if encoder.wait():
                raise RuntimeError('Tracer encoder failed; inspect encoding.log')
    plt.close(fig)
    result = {
        'created_utc': datetime.now(timezone.utc).isoformat(), 'source_checkpoint': args.checkpoint,
        'source_progress_sha256': sha(report_path), 'source_video_sha256': source['video_sha256'],
        'source_cfd_states': source['source_frames'], 'samples_read_and_hash_verified': read_count,
        'equivalent_sample_orderings': len(layouts),
        'first_time_s': float(times[0]), 'last_time_s': physical_time,
        'fps': FPS, 'speed_multiplier': SPEED, 'playback_slowdown': slowdown,
        'encoded_frames': encoded, 'video_duration_s': encoded / FPS,
        'last_frame_file': f'frame-{count - 1:04d}.png',
        'video_sha256': sha(video), 'video_bytes': video.stat().st_size, 'size_px': [width, height],
        'integration': 'Second-order midpoint RK2; maximum 12.5 microseconds; original slice triangles for spatial interpolation; linear temporal interpolation of saved velocity.',
        'visualization': 'Projected 2D tracers follow U_y and U_z on X=+111 mm, not full 3D fluid paths. Pressure is interpolated for display. Random reseeding is visual only, not particle concentration.',
        'particles_per_panel': PARTICLES, 'trail_frames': TRAIL,
        'clouds': [{'respawns_including_initial': c.respawned, 'integrated_particle_steps': c.particle_steps,
                    'integrated_travel_mm': c.travel_mm, 'max_step_displacement_mm': c.max_displacement_mm} for c in clouds],
        'render_seconds': time.monotonic() - started, 'preview': bool(args.preview_frames),
    }
    if extension:
        result['visual_extension'] = extension
    (args.output / 'tracers.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
