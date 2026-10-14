"""Draw the main line and all installed copper cables on one map."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent.parent.parent
CITIES_FILE = ROOT / "data" / "cities.csv"
ROUTE_FILE = ROOT / "results" / "1" / "c_solution.csv"
CONNECTIONS_FILE = ROOT / "results" / "2" / "e_solution.csv"
OUTPUT_FILE = ROOT / "results" / "2" / "e_combined_map.png"

# Read city coordinates, the main line, and copper cable capacities
with open(CITIES_FILE, encoding="utf-8-sig") as f:
    cities = {row["city"]: (float(row["x"]), float(row["y"])) for row in csv.DictReader(f)}
with open(ROUTE_FILE, encoding="utf-8-sig") as f:
    route = [row["city"] for row in sorted(csv.DictReader(f), key=lambda row: int(row["order"]))]
with open(CONNECTIONS_FILE, encoding="utf-8-sig") as f:
    connections = [row for row in csv.DictReader(f) if float(row["capacity_tbps"]) > 1e-6]

STATION_COLORS = {"Warszawa": "tab:blue", "Kielce": "tab:orange", "Opole": "tab:green"}
EXISTING_LINKS = {frozenset(("Radom", "Kielce")), frozenset(("Gliwice", "Opole"))}
LABEL_OFFSETS = {
    "Bytom": (-35, 10), "Gliwice": (-40, -13), "Sosnowiec": (7, 0),
    "Katowice": (6, -14), "Wodzisław Śląski": (-85, -16),
    "Jastrzębie-Zdrój": (8, -5), "Łódź": (-32, -14),
}

fig, ax = plt.subplots(figsize=(16, 13))

# Draw all installed copper cables, colored by destination station
for n, row in enumerate(connections):
    city, station = row["city"], row["station"]
    x, y = cities[city]
    sx, sy = cities[station]
    capacity = float(row["capacity_tbps"])
    color = STATION_COLORS[station]
    ax.plot([x, sx], [y, sy], color=color, linewidth=1.4, alpha=0.65, zorder=1)

    # Spread capacity labels along the cables to reduce overlap
    fraction = {"Warszawa": 0.38, "Kielce": 0.55, "Opole": 0.35}[station]
    fraction += 0.07 * (n % 3)
    ax.annotate(
        f"{capacity:.1f}", (x + fraction * (sx - x), y + fraction * (sy - y)),
        xytext=(0, 4 if n % 2 else -7), textcoords="offset points",
        fontsize=8, color=color, ha="center",
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.9, pad=1), zorder=4,
    )

# Draw the main line above the copper cables
for a, b in zip(route, route[1:]):
    x, y = cities[a]
    sx, sy = cities[b]
    existing = frozenset((a, b)) in EXISTING_LINKS
    ax.plot(
        [x, sx], [y, sy], color="0.4" if existing else "black",
        linestyle="--" if existing else "-", linewidth=2.8, zorder=3,
    )

# Mark and label all cities; stars identify the switching stations
for city, (x, y) in cities.items():
    if city in STATION_COLORS:
        ax.scatter(x, y, marker="*", s=220, color=STATION_COLORS[city], edgecolor="black", zorder=6)
    else:
        ax.scatter(x, y, s=45, color="black" if city in route else "white", edgecolor="black", zorder=5)
    ax.annotate(
        city, (x, y), xytext=LABEL_OFFSETS.get(city, (5, 6)),
        textcoords="offset points", fontsize=9,
        fontweight="bold" if city in route else "normal", zorder=7,
    )

legend = [
    Line2D([0], [0], color="black", linewidth=2.8, label="New main line"),
    Line2D([0], [0], color="0.4", linewidth=2.8, linestyle="--", label="Existing main line link"),
]
for station, color in STATION_COLORS.items():
    legend.append(Line2D([0], [0], color=color, linewidth=1.4, label=f"Copper to {station}"))
ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=3)
ax.set_title("Main line and all copper connections\nCable labels show capacity in TB/s")
ax.set_xlabel("x")
ax.set_ylabel("y")
ax.set_aspect("equal")
ax.margins(0.08)
ax.grid(alpha=0.2)
fig.tight_layout()
fig.savefig(OUTPUT_FILE, dpi=180, bbox_inches="tight", pad_inches=0.2)
plt.close(fig)
print(f"Saved {OUTPUT_FILE}")
