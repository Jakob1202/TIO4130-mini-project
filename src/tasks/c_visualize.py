import csv
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
CITIES_FILE = ROOT / "data" / "cities.csv"
SOLUTION_FILE = ROOT / "results" / "c_solution.csv"
OUTPUT_FILE = ROOT / "results" / "c_map.png"

# Connections that already exist and are not built by the model
EXISTING_LINKS = [("Radom", "Kielce"), ("Gliwice", "Opole")]

AREA_COLORS = {1: "tab:blue", 2: "tab:orange", 3: "tab:green"}

# Cities that are close together get their labels moved so they do not overlap
LABEL_OFFSETS = {"Wodzisław Śląski": (-75, -14), "Bytom": (5, 7), "Katowice": (-48, -14)}

# Read all cities
with open(CITIES_FILE, encoding="utf-8-sig") as f:
    cities = {
        row["city"]: (int(row["area"]), float(row["x"]), float(row["y"]))
        for row in csv.DictReader(f)
    }

# Read the route from the solution file, sorted by visiting order
with open(SOLUTION_FILE, encoding="utf-8-sig") as f:
    rows = sorted(csv.DictReader(f), key=lambda row: int(row["order"]))
route = [row["city"] for row in rows]


fig, ax = plt.subplots(figsize=(11, 10))

# Draw the route, one segment at a time
for a, b in zip(route, route[1:]):
    _, xa, ya = cities[a]
    _, xb, yb = cities[b]

    if (a, b) in EXISTING_LINKS or (b, a) in EXISTING_LINKS:
        ax.plot([xa, xb], [ya, yb], color="grey", linestyle="--", linewidth=2, zorder=1)
    else:
        area = cities[a][0]
        ax.plot([xa, xb], [ya, yb], color=AREA_COLORS[area], linewidth=2.5, zorder=1)

# Draw every city: filled if on the route, hollow if not
for city, (area, x, y) in cities.items():
    on_route = city in route
    ax.scatter(
        x, y, s=70, zorder=3,
        color=AREA_COLORS[area] if on_route else "white",
        edgecolors=AREA_COLORS[area], linewidths=1.5,
    )
    label = f"{route.index(city) + 1}. {city}" if on_route else city
    ax.annotate(label, (x, y), xytext=LABEL_OFFSETS.get(city, (5, 5)), textcoords="offset points",
                fontsize=8, fontweight="bold" if on_route else "normal")

# Legend entries for the line types
for area, color in AREA_COLORS.items():
    ax.plot([], [], color=color, linewidth=2.5, label=f"New cable, area {area}")
ax.plot([], [], color="grey", linestyle="--", linewidth=2, label="Existing link (no cost)")

ax.set_title("Main cable route from Warszawa to Jelenia Góra")
ax.set_xlabel("x")
ax.set_ylabel("y")
ax.set_aspect("equal")
ax.grid(alpha=0.3)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=4, fontsize=8)

fig.tight_layout()
fig.savefig(OUTPUT_FILE, dpi=150)
print(f"Map saved to {OUTPUT_FILE}")
plt.show()
