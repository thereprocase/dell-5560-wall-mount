"""Screen deposited paths and measure prior-layer support for every deposited feature.

This is a geometric toolpath screen, not an ASA bridging or load test. It
distinguishes an entire move's length from its unsupported subsegments.
"""
from pathlib import Path
import argparse
import collections
import json
import hashlib
import math
import re

from shapely.geometry import LineString
from shapely.ops import unary_union
from shapely.prepared import prep


def read_paths(path):
    layers = collections.defaultdict(list)
    x = y = z = e_position = 0.0
    width, feature, relative, active = .42, '', True, False
    header = []
    for line in path.open():
        if line.startswith(';'): header.append(line.rstrip())
        if line.startswith('; Z_HEIGHT:'):
            z, active = float(line.split(':')[1]), True
        if line.startswith('; FEATURE:'): feature = line.split(':', 1)[1].strip()
        if line.startswith('; LINE_WIDTH:'): width = float(line.split(':')[1])
        code = line.split(';')[0].strip()
        if not code: continue
        command = code.split()[0]
        if command == 'M83': relative = True
        if command == 'M82': relative = False
        vals = {k: float(v) for k, v in re.findall(r'([XYZEIJ])(-?\d*\.?\d+)', code)}
        if command == 'G92': e_position = vals.get('E', e_position)
        if command not in ('G0', 'G1', 'G2', 'G3'): continue
        nx, ny = vals.get('X', x), vals.get('Y', y)
        extrusion = vals.get('E', 0 if relative else e_position)
        delta_e = extrusion if relative else extrusion - e_position
        if 'E' in vals: e_position = e_position + extrusion if relative else extrusion
        if active and delta_e > 0 and (nx != x or ny != y) and feature not in ('Custom', 'Brim', 'Flush', 'Skirt'):
            points = [(x, y), (nx, ny)]
            if command in ('G2', 'G3'):
                cx, cy = x + vals.get('I', 0), y + vals.get('J', 0)
                a, b = math.atan2(y - cy, x - cx), math.atan2(ny - cy, nx - cx)
                delta = (b - a) % (2 * math.pi)
                if command == 'G2': delta -= 2 * math.pi
                radius = math.hypot(x - cx, y - cy)
                segments = max(2, math.ceil(abs(delta) * radius / .1))
                points = [(cx + radius * math.cos(a + delta * i / segments),
                           cy + radius * math.sin(a + delta * i / segments)) for i in range(segments + 1)]
            layers[round(z, 4)].append((points, width, feature))
        x, y = nx, ny
    return layers, header


def lines(shape):
    if shape.is_empty: return []
    if shape.geom_type == 'LineString': return [shape]
    return [line for component in getattr(shape, 'geoms', []) for line in lines(component)]


def audit(path, plot=None):
    layers, header = read_paths(path)
    result = {'source_gcode': path.name, 'source_gcode_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'layers': len(layers),
              'method': 'Model paths buffered by reported line width. Island support: previous layer plus 0.15 mm. A deposited bead is supported where it overlaps the prior-layer footprint by at least 0.05 mm: buffer that footprint by half the current bead width minus 0.05 mm. Report contiguous unsupported subsegments, not full move lengths. Same-layer anchoring order and physical sag are not proven.',
              'floating_components': [], 'bridges': [], 'unsupported_paths': [], 'unsupported_by_feature_mm': {}}
    previous, previous_z, worst = None, None, None
    for z, paths in sorted(layers.items()):
        current = unary_union([LineString(points).buffer(width / 2, quad_segs=2) for points, width, feature in paths])
        if previous is not None:
            support = previous.buffer(.15)
            bridge_support_by_width = {}
            prepared_by_width = {}
            for poly in getattr(current, 'geoms', [current]):
                if poly.area > .2 and not poly.intersects(support):
                    result['floating_components'].append({'z_mm': z, 'area_mm2': poly.area, 'bounds_xy_mm': list(poly.bounds)})
            for points, width, feature in paths:
                line = LineString(points)
                if width not in bridge_support_by_width:
                    bridge_support_by_width[width] = previous.buffer(max(0, width / 2 - .05))
                    prepared_by_width[width] = prep(bridge_support_by_width[width])
                bridge_support = bridge_support_by_width[width]
                unsupported = [] if prepared_by_width[width].covers(line) else lines(line.difference(bridge_support))
                longest = max((segment.length for segment in unsupported), default=0)
                row = {'z_mm': z, 'move_length_mm': line.length, 'unsupported_length_mm': longest,
                       'unsupported_total_mm': sum(segment.length for segment in unsupported), 'feature': feature}
                if 'bridge' in feature.lower(): result['bridges'].append(row)
                if longest > 1e-5:
                    result['unsupported_paths'].append(row)
                    result['unsupported_by_feature_mm'][feature] = max(result['unsupported_by_feature_mm'].get(feature, 0), longest)
                if worst is None or longest > worst[0]: worst = (longest, z, paths, previous, unsupported, points)
        previous, previous_z = current, z
    result['max_bridge_move_mm'] = max((r['move_length_mm'] for r in result['bridges']), default=0)
    result['max_unsupported_bridge_span_mm'] = max((r['unsupported_length_mm'] for r in result['bridges']), default=0)
    result['bridge_path_count'] = len(result['bridges'])
    result['bridge_layers'] = sorted({r['z_mm'] for r in result['bridges']})
    result['longest_bridges'] = sorted(result.pop('bridges'), key=lambda x: -x['unsupported_length_mm'])[:20]
    result['max_unsupported_deposition_span_mm'] = max((r['unsupported_length_mm'] for r in result['unsupported_paths']), default=0)
    result['longest_unsupported_paths'] = sorted(result.pop('unsupported_paths'), key=lambda x: -x['unsupported_length_mm'])[:20]
    result['time_and_material_comments'] = [line for line in header if any(t in line for t in ('model printing time:', 'estimated printing time', 'filament used [g]', 'total filament weight', 'filament used [mm]', 'filament used [cm3]'))]
    if plot and worst:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.collections import LineCollection
        from matplotlib.patches import PathPatch
        from matplotlib.path import Path as MplPath
        longest, z, paths, previous, unsupported, points = worst
        fig, axes = plt.subplots(1, 2, figsize=(13, 6))
        for ax in axes:
            for poly in getattr(previous, 'geoms', [previous]):
                vertices, codes = [], []
                for ring in [poly.exterior] + list(poly.interiors):
                    coords = list(ring.coords)
                    vertices.extend(coords)
                    codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(coords) - 2) + [MplPath.CLOSEPOLY])
                ax.add_patch(PathPatch(MplPath(vertices, codes), facecolor='#d5ddd9', edgecolor='none', zorder=0))
            ax.add_collection(LineCollection([a for a, w, f in paths], colors='#1c8489', linewidths=.45))
            ax.add_collection(LineCollection([a for a, w, f in paths if 'bridge' in f.lower()], colors='#d18a18', linewidths=.8))
            ax.add_collection(LineCollection([list(a.coords) for a in unsupported], colors='#c53f50', linewidths=2.5))
            ax.autoscale()
            ax.set_aspect('equal')
            ax.set_xlabel('Plate X / mm')
            ax.set_ylabel('Plate Y / mm')
            ax.set_facecolor('#f7f7f2')
        if unsupported:
            bound = max(unsupported, key=lambda s: s.length).bounds
            axes[1].set_xlim(bound[0] - 5, bound[2] + 5)
            axes[1].set_ylim(bound[1] - 5, bound[3] + 5)
        axes[0].set_title(f'Actual deposited paths at Z = {z:g} mm')
        axes[1].set_title(f'Longest unsupported portion: {longest:.2f} mm')
        fig.suptitle('Teal: model paths   Gold: bridge moves   Red: unsupported portion\nGray: previous-layer extrusion footprint', fontsize=11)
        fig.tight_layout()
        fig.savefig(plot, dpi=160)
        plt.close(fig)
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('gcode', type=Path)
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--plot', type=Path)
    args = ap.parse_args()
    result = audit(args.gcode, args.plot)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('longest_bridges', 'floating_components')}, indent=2))
    print('Floating components:', len(result['floating_components']), flush=True)
