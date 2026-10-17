import csv
import json
import math
import operator
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB

DATA_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "cities.csv"
PARAMS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "main_cable_parameters.json"
RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "results" / "1"

# Define model
m = gp.Model("task_c")

# Read the raw city data: one row per city with area, city, x and y
with open(DATA_FILE, encoding="utf-8-sig") as f:
    cities = list(csv.DictReader(f))

# Read the area parameters (start, end, minimum intermediate cities) and the city constraints
with open(PARAMS_FILE, encoding="utf-8") as f:
    params = json.load(f)
areas = {int(k): area for k, area in params["areas"].items()}

# Sets and indices

# K: geographic areas
K = sorted({int(row["area"]) for row in cities})

# V_k: list of cities in area k
V_k = {k: [row["city"] for row in cities if int(row["area"]) == k] for k in K}

# Starting city s_k and ending city t_k in each area
s_k = {k: areas[k]["start"] for k in K}
t_k = {k: areas[k]["end"] for k in K}

# I_k: intermediate cities (all cities except start and end)
I_k = {k: [i for i in V_k[k] if i not in (s_k[k], t_k[k])] for k in K}

# A_k: all possible directed connections between two different cities in area k
A_k = {k: [(i, j) for i in V_k[k] for j in V_k[k] if i != j] for k in K}

# All connections and all cities across the areas
all_arcs = [(i, j) for k in K for (i, j) in A_k[k]]
all_cities = [i for k in K for i in V_k[k]]

# Parameters

# X_i, Y_i: coordinates of each city
X_i = {row["city"]: float(row["x"]) for row in cities}
Y_i = {row["city"]: float(row["y"]) for row in cities}

# D_ij: Euclidean distance between city i and city j
D_ij = {(i, j): math.sqrt((X_i[i] - X_i[j]) ** 2 + (Y_i[i] - Y_i[j]) ** 2) for (i, j) in all_arcs}

# M_k: number of cities in area k
M_k = {k: len(V_k[k]) for k in K}

# R_k: minimum number of intermediate cities in area k
R_k = {k: areas[k]["min_intermediate"] for k in K}

# C: construction cost per unit of cable length
C = params["cost_per_length"]

# Variables

# x_ij = 1 if connection (i, j) is selected
x_ij = m.addVars(all_arcs, vtype=GRB.BINARY, name="x")

# y_i = 1 if city i is included in the route
y_i = m.addVars(all_cities, vtype=GRB.BINARY, name="y")

# Objective function
m.setObjective(
    C * gp.quicksum(D_ij[i, j] * x_ij[i, j] for k in K for (i, j) in A_k[k]),
    GRB.MINIMIZE,
)

# Constraints
for k in K:
    start, end = s_k[k], t_k[k]

    # (1) Exactly one connection leaves the starting city
    m.addConstr(gp.quicksum(x_ij[start, j] for j in V_k[k] if j != start) == 1, name=f"start_out_{k}")

    # (2) No connection enters the starting city
    m.addConstr(gp.quicksum(x_ij[i, start] for i in V_k[k] if i != start) == 0, name=f"start_in_{k}")

    # (3) Exactly one connection enters the ending city
    m.addConstr(gp.quicksum(x_ij[i, end] for i in V_k[k] if i != end) == 1, name=f"end_in_{k}")

    # (4) No connection leaves the ending city
    m.addConstr(gp.quicksum(x_ij[end, j] for j in V_k[k] if j != end) == 0, name=f"end_out_{k}")

    # (5) Starting and ending cities are always included
    m.addConstr(y_i[start] == 1, name=f"include_start_{k}")
    m.addConstr(y_i[end] == 1, name=f"include_end_{k}")

    for i in I_k[k]:
        # (6) A selected intermediate city has exactly one outgoing connection
        m.addConstr(gp.quicksum(x_ij[i, j] for j in V_k[k] if j != i) == y_i[i], name=f"out_{i}")

        # (7) A selected intermediate city has exactly one incoming connection
        m.addConstr(gp.quicksum(x_ij[j, i] for j in V_k[k] if j != i) == y_i[i], name=f"in_{i}")

    # (8) Minimum number of intermediate cities in each area
    m.addConstr(gp.quicksum(y_i[i] for i in I_k[k]) >= R_k[k], name=f"min_cities_{k}")

# (9)-(12) Constraints on which cities are included, read from the parameter file:
# sum of y_i over the listed cities (<=, >= or ==) rhs
SENSES = {"<=": operator.le, ">=": operator.ge, "==": operator.eq}
for con in params["city_constraints"]:
    lhs = gp.quicksum(y_i[i] for i in con["cities"])
    m.addConstr(SENSES[con["sense"]](lhs, con["rhs"]), name=con["name"])

for k in K:
    # (13) A pair of cities can only be connected in one direction
    for (i, j) in A_k[k]:
        if i < j:  # add each pair only once
            m.addConstr(x_ij[i, j] + x_ij[j, i] <= 1, name=f"one_direction_{i}_{j}")

# (14) - (15) Nonnegativity is handled by the variable bounds above

# Solve the model
m.optimize()

if m.status == GRB.OPTIMAL:
    print(f"\nThe length of the main cable: {m.ObjVal:.2f}")
    routes = {}
    lengths = {}

    # Construct the route for each area
    for k in K:
        route = [s_k[k]]

        while route[-1] != t_k[k]:
            current = route[-1]
            next_city = next(
                j for j in V_k[k]
                if j != current and x_ij[current, j].X > 0.5
            )
            route.append(next_city)

        routes[k] = route
        lengths[k] = sum(
            D_ij[route[n], route[n + 1]]
            for n in range(len(route) - 1)
        )

    # Print the complete main cable route
    full_route = [city for k in K for city in routes[k]]

    print(f"\nThe cities connected by the main cable in order. Starting from {s_k[K[0]]}\n")
    print(" -> ".join(full_route))

    # Print routes distinguished by area
    print("\nRoutes sorted by area:\n")
    for k in K:
        print(f"Area {k}: {' -> '.join(routes[k])}")
        print(f"Length: {lengths[k]:.2f}\n")

    # Save the main cable route to results/1/c_solution.csv
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    city_area = {city: k for k in K for city in V_k[k]}

    with open(RESULTS_DIR / "c_solution.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["order", "area", "city", "x", "y"])
        for order, city in enumerate(full_route, start=1):
            writer.writerow([order, city_area[city], city, X_i[city], Y_i[city]])
else:
    print("No optimal solution found.")
