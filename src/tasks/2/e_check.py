"""Independent checker for case E (copper connections to the switching stations).

Written from the case text (task e and the copper cable information) and the format of
the solution files only, without the optimization model or its formulation. Reads
results/1/c_solution.csv (fixed main line), results/2/e_solution.csv (one row per
city-station cable), results/2/e_stations.csv and results/2/e_summary.json, and checks
every requirement in the case. Prints PASS/FAIL per check and exits with status 1 if
anything fails.

Coordinates and demands are copied from Table 1 in the case text, so data/cities.csv
is checked against the case instead of being trusted.

Interpretations of the case text (decided here, since the text is not explicit):
- Every city in Table 1 that the main line does not pass through must be connected.
  Warszawa, Kielce and Opole are stations and lie on the main line anyway.
- "Connected" means the total installed capacity from the city covers its demand.
- A row with capacity 0 means no cable is laid between that city and station.
- The distance limit x <= 2*pi*min(35, 70 - d) and the 200 TB/s limit apply to each
  cable separately.
- The Łódź 40% rule applies to Łódź's total outgoing flow, i.e. the sum over its cables.
- Capacities and costs are compared with a small tolerance (1e-6 relative/absolute).
"""
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CITIES_FILE = ROOT / "data" / "cities.csv"
MAIN_LINE_FILE = ROOT / "results" / "1" / "c_solution.csv"
SOLUTION_FILE = ROOT / "results" / "2" / "e_solution.csv"
STATIONS_FILE = ROOT / "results" / "2" / "e_stations.csv"
SUMMARY_FILE = ROOT / "results" / "2" / "e_summary.json"

# Table 1 in the case text: city -> (x, y, demand in TB/s); None for station cities
CASE_CITIES = {
    "Warszawa": (100, 65, None), "Skierniewice": (92, 62, 197), "Łódź": (85, 58, 317),
    "Konin": (68, 64, 236), "Sieradz": (72, 55, 178), "Piotrków": (89, 51, 139),
    "Radom": (102, 50, 288),
    "Kielce": (98, 42, None), "Częstochowa": (79, 40, 278), "Bytom": (76, 31, 163),
    "Gliwice": (73, 30, 105), "Sosnowiec": (80, 29, 143), "Kraków": (89, 25, 331),
    "Bielsko": (79, 20, 276), "Katowice": (78, 28, 263), "Jastrzębie-Zdrój": (74, 23, 137),
    "Wodzisław Śląski": (71, 23, 119),
    "Poznań": (54, 68, 251), "Zielona Góra": (39, 60, 121), "Leszno": (51, 58, 84),
    "Kalisz": (65, 58, 207), "Legnica": (45, 47, 176), "Wrocław": (54, 45, 133),
    "Jelenia Góra": (40, 42, 167), "Wałbrzych": (46, 39, 129), "Opole": (67, 37, None),
}

# Switching stations: one unit of 400 TB/s in Opole, two in Warszawa, three in Kielce
UNIT_CAPACITY = 400
STATIONS = {"Warszawa": 2 * UNIT_CAPACITY, "Kielce": 3 * UNIT_CAPACITY, "Opole": 1 * UNIT_CAPACITY}
MAX_CABLE = 200            # TB/s per copper cable
PRICE = 1000               # EUR per coordinate unit and TB/s
LODZ_MAX_SHARE = 0.4       # share of Łódź's total flow in a single cable
TOL = 1e-6

results = []

def check(name, ok, detail=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))

def close(a, b):
    return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))

def dist(a, b):
    return math.hypot(CASE_CITIES[a][0] - CASE_CITIES[b][0], CASE_CITIES[a][1] - CASE_CITIES[b][1])

def distance_limit(d):
    return 2 * math.pi * min(35, 70 - d)

# --- load data ---------------------------------------------------------------
with open(CITIES_FILE, encoding="utf-8-sig", newline="") as f:
    data_rows = list(csv.DictReader(f))
with open(MAIN_LINE_FILE, encoding="utf-8-sig", newline="") as f:
    main_line = [r["city"].strip() for r in csv.DictReader(f)]
with open(SOLUTION_FILE, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
with open(STATIONS_FILE, encoding="utf-8-sig", newline="") as f:
    station_rows = list(csv.DictReader(f))
with open(SUMMARY_FILE, encoding="utf-8") as f:
    summary = json.load(f)

print(f"Loaded {len(rows)} cable rows, main line with {len(main_line)} cities\n")

# --- data consistency with the case text ------------------------------------
data_ok = len(data_rows) == len(CASE_CITIES)
for r in data_rows:
    name = r["city"].strip()
    if name not in CASE_CITIES:
        data_ok = False
        continue
    x, y, q = CASE_CITIES[name]
    demand = float(r["demand_tbps"]) if r["demand_tbps"].strip() else None
    if float(r["x"]) != x or float(r["y"]) != y or demand != q:
        data_ok = False
check("cities.csv matches Table 1 in the case (names, coordinates, demands)", data_ok)
check("Main line cities exist in the case", all(c in CASE_CITIES for c in main_line))

# --- file format -------------------------------------------------------------
expected_cols = ["city", "station", "distance", "demand_tbps", "max_capacity_tbps", "capacity_tbps", "cost_eur"]
check("Columns of e_solution.csv", rows and list(rows[0].keys()) == expected_cols,
      str(list(rows[0].keys())) if rows else "empty file")

cap = {}
for r in rows:
    key = (r["city"].strip(), r["station"].strip())
    cap[key] = cap.get(key, []) + [float(r["capacity_tbps"])]
cables = {key: vals[0] for key, vals in cap.items()}
used = {key: x for key, x in cables.items() if x > TOL}

# --- who must be connected ---------------------------------------------------
to_connect = [c for c in CASE_CITIES if c not in main_line]
print("Cities to connect:", ", ".join(to_connect), "\n")
check("Stations Warszawa, Kielce and Opole lie on the main line",
      all(s in main_line for s in STATIONS))
check("Only cities off the main line have cables",
      all(c in to_connect for (c, _) in used),
      str(sorted({c for (c, _) in used if c not in to_connect})))
check("Cables only go to Warszawa, Kielce or Opole",
      all(s in STATIONS for (_, s) in cables),
      str(sorted({s for (_, s) in cables if s not in STATIONS})))

# --- cable rules -------------------------------------------------------------
check("No parallel cables (at most one cable per city-station pair)",
      all(len(v) == 1 for v in cap.values()),
      str([k for k, v in cap.items() if len(v) > 1]))
check("No negative capacities", all(x >= -TOL for x in cables.values()))
over_max = [(c, s, round(x, 3)) for (c, s), x in used.items() if x > MAX_CABLE + TOL]
check(f"Every cable carries at most {MAX_CABLE} TB/s", not over_max, str(over_max))
over_dist = [(c, s, round(x, 3), round(distance_limit(dist(c, s)), 3))
             for (c, s), x in used.items() if x > distance_limit(dist(c, s)) + TOL]
check("Every cable satisfies x <= 2*pi*min(35, 70 - d)", not over_dist, str(over_dist))

# --- demand ------------------------------------------------------------------
for c in to_connect:
    total = sum(x for (ci, _), x in used.items() if ci == c)
    q = CASE_CITIES[c][2]
    n = sum(1 for (ci, _) in used if ci == c)
    check(f"{c}: demand {q} TB/s covered", total >= q - TOL,
          f"{total:.3f} TB/s over {n} cable(s)" + ("" if close(total, q) else " (spare capacity)"))

# --- Łódź --------------------------------------------------------------------
if "Łódź" in to_connect:
    lodz = {s: x for (c, s), x in used.items() if c == "Łódź"}
    total = sum(lodz.values())
    check("Łódź: at most 40% of its total flow in a single cable",
          all(x <= LODZ_MAX_SHARE * total + TOL for x in lodz.values()),
          ", ".join(f"{s} {x / total:.1%}" for s, x in lodz.items()))

# --- stations ----------------------------------------------------------------
load = {s: sum(x for (_, si), x in used.items() if si == s) for s in STATIONS}
for s, b in STATIONS.items():
    check(f"Station {s}: load within {b} TB/s", load[s] <= b + TOL,
          f"{load[s]:.3f} TB/s ({load[s] / b:.3%})")
reported = {r["station"].strip(): r for r in station_rows}
check("e_stations.csv agrees with recomputed station loads",
      all(s in reported and close(float(reported[s]["installed_tbps"]), STATIONS[s])
          and close(float(reported[s]["utilized_tbps"]), load[s]) for s in STATIONS))

# --- reported columns and cost -----------------------------------------------
cols_ok = all(
    close(float(r["distance"]), dist(r["city"].strip(), r["station"].strip()))
    and close(float(r["demand_tbps"]), CASE_CITIES[r["city"].strip()][2])
    and close(float(r["max_capacity_tbps"]),
              min(MAX_CABLE, distance_limit(dist(r["city"].strip(), r["station"].strip()))))
    and close(float(r["cost_eur"]),
              PRICE * dist(r["city"].strip(), r["station"].strip()) * float(r["capacity_tbps"]))
    for r in rows
)
check("Reported distance, demand, cable limit and cost agree with the case", cols_ok)

total_cost = sum(PRICE * dist(c, s) * x for (c, s), x in used.items())
check("Total cost agrees with e_summary.json", close(total_cost, summary["total_cost_eur"]),
      f"{total_cost:,.2f} EUR vs {summary['total_cost_eur']:,.2f} EUR")

# --- answers to the questions in task e --------------------------------------
print("\nAnswers to task e:")
print(f"  Cost of connecting the remaining cities: {total_cost:,.2f} EUR")
for c in ("Poznań", "Wałbrzych"):
    caps = ", ".join(f"{s} {cables.get((c, s), 0.0):.3f}" for s in STATIONS)
    print(f"  {c}: {caps} TB/s")
print(f"  Kielce utilization: {load['Kielce']:.3f} of {STATIONS['Kielce']} TB/s "
      f"({load['Kielce'] / STATIONS['Kielce']:.3%})")

print(f"\nSummary: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
