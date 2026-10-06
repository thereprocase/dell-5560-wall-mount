"""Plot the measured native sections, keeping geometry and strength distinct."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / 'reports/wall-transition-review.json').read_text())['presets']['5560']
rows = data['junctions']['lower']['sections']
fig = plt.figure(figsize=(10, 8.3), facecolor='white', layout='constrained')
grid = fig.add_gridspec(2, 2, height_ratios=[1.5, 1])
colors = {'before': '#546268', 'after': '#b89143'}
for column, key, title in [(0, 'before', 'M1 / original junction'), (1, 'after', 'M1.1 / paired tapered webs')]:
    ax = fig.add_subplot(grid[0, column])
    record = rows[0][key]
    for loop in record['profile_y_z_from_bolt_mm']:
        ax.add_patch(Polygon(loop, facecolor=colors[key], edgecolor='#25363b', lw=1.2))
    ax.set(xlim=(-2, 28), ylim=(-19, 19), aspect='equal', xlabel='Distance from wall, Y (mm)',
           ylabel='Height from bolt center, Z (mm)', title=title)
    ax.text(.95, .95, f"{record['area_mm2']:.0f} mm²", transform=ax.transAxes, ha='right', va='top',
            fontsize=17, fontweight='bold', color='#25363b')
    ax.axvline(0, c='#25363b', lw=.6, ls=':')
    ax.spines[['top', 'right']].set_visible(False)
ax = fig.add_subplot(grid[1, :])
for key, label in [('before', 'Original M1'), ('after', 'Reinforced M1.1')]:
    ax.plot([r[key]['print_height_mm'] for r in rows], [r[key]['area_mm2'] for r in rows],
            '-o', color=colors[key], label=label, lw=2, markersize=4)
ax.set(xlabel='Print height above the outer arm face (mm)', ylabel='Net junction area (mm²)',
       title='Sampled sections through one wall pad')
ax.grid(axis='y', alpha=.2)
ax.legend(frameon=False)
ax.spines[['top', 'right']].set_visible(False)
fig.suptitle('Spreading the arm-to-wall transition across the printed layers', fontsize=15, fontweight='bold')
fig.supxlabel('Native 5560 geometry • upper profiles at 12.02 mm print height • area ratios are not tested strength multipliers', fontsize=9)
out = ROOT.parent / 'docs/assets/minimalist-wall-transition-section'
fig.savefig(out.with_suffix('.png'), dpi=160)
fig.savefig(out.with_suffix('.svg'))
# Retain path separators while avoiding trailing whitespace in generated SVG.
svg = out.with_suffix('.svg')
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
plt.close(fig)
