import csv
import json
import math
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_FILE = ROOT / "data" / "cities.csv"
PARAMETERS_FILE = ROOT / "data" / "copper_parameters.json"
ROUTE_FILE = ROOT / "results" / "1" / "c_solution.csv"
RESULTS_DIR = ROOT / "results" / "2"

# Define model
m = gp.Model("task_e")

# Read city data, the main cable route, and copper cable parameters
with open(DATA_FILE, encoding="utf-8-sig") as f:
    cities = list(csv.DictReader(f))

with open(ROUTE_FILE, encoding="utf-8-sig") as f:
    main_cities = [row["city"] for row in csv.DictReader(f)]

with open(PARAMETERS_FILE, encoding="utf-8") as f:
    parameters = json.load(f)

# Sets and indices

# N: cities not visited by the main cable
N = [row["city"] for row in cities if row["city"] not in main_cities]

# S: switching stations
S = list(parameters["stations"])

# Parameters

# Coordinates and demand of each remaining city
X_i = {row["city"]: float(row["x"]) for row in cities}
Y_i = {row["city"]: float(row["y"]) for row in cities}
Q_i = {row["city"]: float(row["demand_tbps"]) for row in cities if row["city"] in N}

# B_s: available capacity at each station
B_s = parameters["stations"]

# C: cable cost per coordinate unit and TB/s
C = parameters["cost_eur_per_length_tbps"]

# D_is: Euclidean distance from city i to station s
D_is = {
    (i, s): math.sqrt((X_i[i] - X_i[s]) ** 2 + (Y_i[i] - Y_i[s]) ** 2)
    for i in N for s in S
}

# E: connections with positive distance-dependent capacity
E = [(i, s) for i in N for s in S if D_is[i, s] < parameters["distance_cutoff"]]

# U_is: maximum capacity, including the 200 TB/s and distance limits
U_is = {
    (i, s): min(
        parameters["max_cable_tbps"],
        2 * math.pi * min(parameters["distance_plateau"], parameters["distance_cutoff"] - D_is[i, s]),
    )
    for i, s in E
}

# Variables

# f_is: capacity installed between city i and station s, in TB/s
f_is = m.addVars(E, lb=0, vtype=GRB.CONTINUOUS, name="f")

# Objective function
m.setObjective(
    C * gp.quicksum(D_is[i, s] * f_is[i, s] for i, s in E),
    GRB.MINIMIZE,
)

# Constraints

# (1) Meet every remaining city's demand
for i in N:
    m.addConstr(
        gp.quicksum(f_is[i, s] for s in S if (i, s) in E) == Q_i[i],
        name=f"demand_{i}",
    )

# (2) Respect each switching station's capacity
for s in S:
    m.addConstr(
        gp.quicksum(f_is[i, s] for i in N if (i, s) in E) <= B_s[s],
        name=f"station_{s}",
    )

# (3) Respect each cable's capacity limit
for i, s in E:
    m.addConstr(f_is[i, s] <= U_is[i, s], name=f"cable_{i}_{s}")

# (4) Each cable from Łódź carries at most 40% of its demand
if "Łódź" in N:
    for s in S:
        if ("Łódź", s) in E:
            m.addConstr(
                f_is["Łódź", s] <= parameters["lodz_max_share"] * Q_i["Łódź"],
                name=f"lodz_{s}",
            )

# Nonnegativity is handled by the variable bounds above

# Solve the model
m.optimize()

if m.status == GRB.OPTIMAL:
    print(f"\nTotal copper cable cost: EUR {m.ObjVal:,.2f}")

    # Print the capacities requested in the assignment
    for i in ["Poznań", "Wałbrzych"]:
        if i in N:
            for s in S:
                capacity = f_is[i, s].X if (i, s) in E else 0
                print(f"{i} -> {s}: {capacity:.3f} TB/s")

    # Calculate and print station utilization
    station_rows = []
    for s in S:
        used = sum(f_is[i, s].X for i in N if (i, s) in E)
        percentage = 100 * used / B_s[s]
        print(f"{s}: {used:.3f}/{B_s[s]} TB/s ({percentage:.2f}%)")
        station_rows.append([s, B_s[s], used, percentage])

    # Save all capacities, including unused connections
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    solution_rows = []
    for i in N:
        for s in S:
            capacity = f_is[i, s].X if (i, s) in E else 0
            cost = C * D_is[i, s] * capacity
            solution_rows.append([i, s, D_is[i, s], Q_i[i], U_is.get((i, s), 0), capacity, cost])

    with open(RESULTS_DIR / "e_solution.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["city", "station", "distance", "demand_tbps", "max_capacity_tbps", "capacity_tbps", "cost_eur"])
        writer.writerows(solution_rows)

    with open(RESULTS_DIR / "e_stations.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["station", "installed_tbps", "utilized_tbps", "utilization_pct"])
        writer.writerows(station_rows)

    # Save dual values and RHS ranges for analysis of the LP
    with open(RESULTS_DIR / "e_duals.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["constraint", "shadow_price", "slack", "rhs", "allowable_rhs_min", "allowable_rhs_max"])
        for constraint in m.getConstrs():
            writer.writerow([
                constraint.ConstrName, constraint.Pi, constraint.Slack,
                constraint.RHS, constraint.SARHSLow, constraint.SARHSUp,
            ])

    with open(RESULTS_DIR / "e_summary.json", "w", encoding="utf-8") as f:
        json.dump({
            "total_cost_eur": m.ObjVal,
            "cities_connected": len(N),
            "positive_cables": sum(f_is[i, s].X > 1e-6 for i, s in E),
            "pi": math.pi,
        }, f, indent=2)
else:
    raise RuntimeError("No optimal solution found. Existing results were not overwritten.")
