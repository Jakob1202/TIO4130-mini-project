import csv
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
CITIES_FILE = ROOT / "data" / "cities.csv"
ARCS_FILE = ROOT / "results" / "c_broken_arcs.csv"
OUTPUT_FILE = ROOT / "results" / "c_broken_map.png"

# Connections that already exist and are not built by the model
EXISTING_LINKS = [("Radom", "Kielce"), ("Gliwice", "Opole")]

AREA_COLORS = {1: "tab:blue", 2: "tab:orange", 3: "tab:green"}
LOOP_COLOR = "tab:red"

# Cities that are close together get their labels moved so they do not overlap
LABEL_OFFSETS = {"Wodzisław Śląski": (-75, -14), "Bytom": (5, 7), "Katowice": (-48, -14)}


# Read all cities
with open(CITIES_FILE, encoding="utf-8-sig") as f:
    cities = {
        row["city"]: (int(row["area"]), float(row["x"]), float(row["y"]))
        for row in csv.DictReader(f)
    }

# Read every connection selected by the broken model
with open(ARCS_FILE, encoding="utf-8-sig") as f:
    arcs = list(csv.DictReader(f))

used_cities = {row["from"] for row in arcs} | {row["to"] for row in arcs}


fig, ax = plt.subplots(figsize=(11, 10))

# Draw the selected connections. Connections on the main cable get the area color,
# connections in a loop (both directions selected) are drawn in red.
for row in arcs:
    _, xa, ya = cities[row["from"]]
    _, xb, yb = cities[row["to"]]

    if row["two_way"] == "True":
        ax.plot([xa, xb], [ya, yb], color=LOOP_COLOR, linewidth=4, zorder=1)
    else:
        ax.plot([xa, xb], [ya, yb], color=AREA_COLORS[int(row["area"])], linewidth=2.5, zorder=1)

# Draw the existing connections between the areas
for a, b in EXISTING_LINKS:
    _, xa, ya = cities[a]
    _, xb, yb = cities[b]
    ax.plot([xa, xb], [ya, yb], color="grey", linestyle="--", linewidth=2, zorder=1)

# Draw every city: filled if it has a selected connection, hollow if not
for city, (area, x, y) in cities.items():
    used = city in used_cities
    ax.scatter(
        x, y, s=70, zorder=3,
        color=AREA_COLORS[area] if used else "white",
        edgecolors=AREA_COLORS[area], linewidths=1.5,
    )
    ax.annotate(city, (x, y), xytext=LABEL_OFFSETS.get(city, (5, 5)), textcoords="offset points",
                fontsize=8, fontweight="bold" if used else "normal")

# Legend entries for the line types
for area, color in AREA_COLORS.items():
    ax.plot([], [], color=color, linewidth=2.5, label=f"New cable, area {area}")
ax.plot([], [], color=LOOP_COLOR, linewidth=4, label="Loop: connected in both directions")
ax.plot([], [], color="grey", linestyle="--", linewidth=2, label="Existing link (no cost)")

ax.set_title("Broken model: all selected connections")
ax.set_xlabel("x")
ax.set_ylabel("y")
ax.set_aspect("equal")
ax.grid(alpha=0.3)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3, fontsize=8)

fig.tight_layout()
fig.savefig(OUTPUT_FILE, dpi=150)
print(f"Map saved to {OUTPUT_FILE}")
plt.show()
