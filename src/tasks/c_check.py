"""Independent checker for case C (MobiPhlex main line, Warszawa -> Jelenia Góra).

Reads data/cities.csv and results/c_solution.csv and checks every requirement in the
case text. Prints PASS/FAIL per check and exits with status 1 if anything fails.

Interpretations of the case text (decided here, since the text is not explicit):
- "pass through at least N other cities" in an area means at least N cities
  belonging to that area (per cities.csv), other than the area's start and end.
- The line is built area by area: all area-1 cities, then all area-2, then all
  area-3. The only connections that cross areas are the two existing links
  Radom-Kielce and Gliwice-Opole, and those must actually be used (they are
  "part of the main line").
- The group rules (Konin/Kalisz etc.) apply to the whole line, regardless of
  which area the cities belong to.
- Coordinates are compared with a small tolerance (1e-6).
- New cable length = sum of Euclidean distances over all consecutive pairs,
  excluding the two existing links (cost zero).
"""
import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CITIES_FILE = ROOT / "data" / "cities.csv"
SOLUTION_FILE = ROOT / "results" / "c_solution.csv"

AREAS = {1: ("Warszawa", "Radom", 2), 2: ("Kielce", "Gliwice", 3), 3: ("Opole", "Jelenia Góra", 3)}
EXISTING_LINKS = {frozenset(("Radom", "Kielce")), frozenset(("Gliwice", "Opole"))}

results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


# --- load data ---------------------------------------------------------------
with open(CITIES_FILE, encoding="utf-8-sig", newline="") as f:
    cities = {r["city"].strip(): (int(r["area"]), float(r["x"]), float(r["y"])) for r in csv.DictReader(f)}

with open(SOLUTION_FILE, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

print(f"Loaded {len(cities)} cities and {len(rows)} route rows\n")

# --- file format -------------------------------------------------------------
check("Columns are order,area,city,x,y",
      rows and list(rows[0].keys()) == ["order", "area", "city", "x", "y"],
      str(list(rows[0].keys())) if rows else "empty file")
orders = [int(r["order"]) for r in rows]
check("Order column runs 1..n without gaps", orders == list(range(1, len(rows) + 1)), str(orders))
rows.sort(key=lambda r: int(r["order"]))
route = [r["city"].strip() for r in rows]
print("Route:", " -> ".join(route), "\n")

# --- cities exist and data match cities.csv ----------------------------------
unknown = [c for c in route if c not in cities]
check("Every city exists in cities.csv", not unknown, f"unknown: {unknown}" if unknown else "")
mismatch = []
for r in rows:
    c = r["city"].strip()
    if c in cities:
        area, x, y = cities[c]
        if int(r["area"]) != area or abs(float(r["x"]) - x) > 1e-6 or abs(float(r["y"]) - y) > 1e-6:
            mismatch.append(c)
check("Area and coordinates match cities.csv", not mismatch, f"mismatch: {mismatch}" if mismatch else "")
if unknown:
    print("\nCannot continue with unknown cities.")
    sys.exit(1)

# --- start / end -------------------------------------------------------------
check("Route starts in Warszawa", route[0] == "Warszawa", route[0])
check("Route ends in Jelenia Góra", route[-1] == "Jelenia Góra", route[-1])

# --- no loops / single continuous route --------------------------------------
dupes = sorted({c for c in route if route.count(c) > 1})
check("No city visited more than once (no loops)", not dupes, f"repeated: {dupes}" if dupes else "")
# A list of rows where consecutive rows are connected is a single path by
# construction; with no repeated cities it is a simple path from start to end.
check("One continuous route (simple path, every row linked to the next)",
      not dupes and len(route) >= 2, f"{len(route)} cities, {len(route) - 1} connections")
edges = [frozenset((a, b)) for a, b in zip(route, route[1:])]
check("No duplicate connection between any pair", len(edges) == len(set(edges)))
check("No self-connection", all(len(e) == 2 for e in edges))

# --- area order --------------------------------------------------------------
area_seq = [cities[c][0] for c in route]
blocks = [a for i, a in enumerate(area_seq) if i == 0 or a != area_seq[i - 1]]
check("Areas visited in order 1 -> 2 -> 3, each as one block", blocks == [1, 2, 3], f"blocks: {blocks}")

# --- per-area start, end and number of intermediate cities -------------------
for area, (start, end, need) in AREAS.items():
    part = [c for c in route if cities[c][0] == area]
    if not part:
        check(f"Area {area}: present", False)
        continue
    check(f"Area {area}: starts in {start}", part[0] == start, part[0])
    check(f"Area {area}: ends in {end}", part[-1] == end, part[-1])
    others = [c for c in part if c not in (start, end)]
    check(f"Area {area}: at least {need} other cities", len(others) >= need, f"{len(others)}: {others}")

# --- connections stay within an area, except the existing links --------------
bad = []
for a, b in zip(route, route[1:]):
    if cities[a][0] != cities[b][0] and frozenset((a, b)) not in EXISTING_LINKS:
        bad.append(f"{a}-{b}")
check("Every connection stays within one area (except existing links)", not bad,
      f"cross-area: {bad}" if bad else "")
for link in EXISTING_LINKS:
    a, b = sorted(link)
    check(f"Existing link {a}-{b} is used", link in edges)

# --- group rules -------------------------------------------------------------
on = set(route)


def count(*names):
    return sorted(n for n in names if n in on)


k = count("Konin", "Kalisz")
check("At least one of Konin, Kalisz", len(k) >= 1, f"included: {k}")
k = count("Bytom", "Sosnowiec", "Katowice")
check("At most one of Bytom, Sosnowiec, Katowice", len(k) <= 1, f"included: {k}")
k = count("Wodzisław Śląski", "Jastrzębie-Zdrój")
check("Not both Wodzisław Śląski and Jastrzębie-Zdrój", len(k) <= 1, f"included: {k}")
k = count("Poznań", "Zielona Góra", "Leszno")
check("At least one of Poznań, Zielona Góra, Leszno", len(k) >= 1, f"included: {k}")

# --- cable length ------------------------------------------------------------
print("\nCable length (Euclidean):")
per_area = {1: 0.0, 2: 0.0, 3: 0.0}
for a, b in zip(route, route[1:]):
    d = dist(cities[a][1:], cities[b][1:])
    if frozenset((a, b)) in EXISTING_LINKS:
        print(f"  {a:>18} - {b:<18} {d:8.3f}  (existing, cost 0)")
        continue
    per_area[cities[a][0]] += d
    print(f"  {a:>18} - {b:<18} {d:8.3f}  (area {cities[a][0]})")
for area, length in per_area.items():
    print(f"  Area {area}: {length:.3f}")
print(f"  Total new cable: {sum(per_area.values()):.3f}")

# --- summary -----------------------------------------------------------------
failed = results.count(False)
print(f"\nSummary: {len(results) - failed}/{len(results)} checks passed"
      + ("" if not failed else f", {failed} FAILED"))
sys.exit(1 if failed else 0)
