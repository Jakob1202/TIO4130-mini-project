"""Draw copper capacity allocations together with the fixed main cable route."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent.parent



# Read all city coordinates
with open(ROOT / 'data/cities.csv', encoding='utf-8-sig') as f:
    cities = {r['city']: (float(r['x']), float(r['y'])) for r in csv.DictReader(f)}
# Read the main route in visiting order
with open(ROOT / 'results/1/c_solution.csv', encoding='utf-8-sig') as f:
    route = [r['city'] for r in sorted(csv.DictReader(f), key=lambda r: int(r['order']))]
# Read the copper capacities
with open(ROOT / 'results/2/e_solution.csv', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
colors = {'Warszawa': 'tab:blue', 'Kielce': 'tab:orange', 'Opole': 'tab:green'}
fig, axes = plt.subplots(1, 3, figsize=(21, 9), sharex=True, sharey=True)
for ax, (station, color) in zip(axes, colors.items()):
    for a, b in zip(route, route[1:]):
        ax.plot([cities[a][0], cities[b][0]], [cities[a][1], cities[b][1]], color='0.8', linewidth=1, zorder=1)
    for city, xy in cities.items():
        ax.scatter(*xy, s=18, color='0.65', zorder=3)
        ax.annotate(city, xy, xytext=(3, 3), textcoords='offset points', fontsize=6)
    selected = [r for r in rows if r['station'] == station and float(r['capacity_tbps']) > 1e-6]
    for n, r in enumerate(selected):
        x, y = cities[r['city']]
        sx, sy = cities[station]
        f = float(r['capacity_tbps'])
        ax.plot([x, sx], [y, sy], color=color, alpha=.7, linewidth=1 + f / 100, zorder=2)
        fraction = .3 + .08 * (n % 4)
        ax.annotate(f'{f:.1f}', (x + fraction * (sx-x), y + fraction * (sy-y)), fontsize=7, color=color, bbox=dict(facecolor='white', edgecolor='none', alpha=.85, pad=1))
    ax.scatter(*cities[station], marker='*', s=180, color=color, zorder=4)
    ax.set_title(f'{station}: {sum(float(r["capacity_tbps"]) for r in selected):.1f} TB/s')
    ax.set_aspect('equal')
    ax.set_xlabel('x')
    ax.grid(alpha=.2)
axes[0].set_ylabel('y')
fig.suptitle('Copper connections: cable labels in TB/s; fixed main line in gray')
fig.tight_layout()
fig.savefig(ROOT / 'results/2/e_map.png', dpi=160)
plt.close(fig)
print('Saved results/2/e_map.png')
