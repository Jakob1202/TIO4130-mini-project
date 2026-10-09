import csv
import math
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "cities.csv"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

USE_ONE_DIRECTION = False  # constraint (13)
USE_SUBTOUR_ELIMINATION = False  # constraint (14)

# Define model
m = gp.Model("task_c_broken")

# Read the raw city data: one row per city with area, city, x and y
with open(DATA_FILE, encoding="utf-8-sig") as f:
    cities = list(csv.DictReader(f))

# Sets and indices

# K: geographic areas (1, 2, 3)
K = sorted({int(row["area"]) for row in cities})

# V_k: list of cities in area k
V_k = {k: [row["city"] for row in cities if int(row["area"]) == k] for k in K}

# Starting city s_k and ending city t_k in each area
s_k = {1: "Warszawa", 2: "Kielce", 3: "Opole"}
t_k = {1: "Radom", 2: "Gliwice", 3: "Jelenia Góra"}

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
R_k = {1: 2, 2: 3, 3: 3}

# C: construction cost per unit of cable length (assumed to be 1 for simplicity)
C = 1

# Variables

# x_ij = 1 if connection (i, j) is selected
x_ij = m.addVars(all_arcs, vtype=GRB.BINARY, name="x")

# y_i = 1 if city i is included in the route
y_i = m.addVars(all_cities, vtype=GRB.BINARY, name="y")

# u_i = position of city i in the route within its area
u_i = m.addVars(all_cities, lb=0, vtype=GRB.CONTINUOUS, name="u")


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

# (9) At least one of Konin and Kalisz
m.addConstr(y_i["Konin"] + y_i["Kalisz"] >= 1, name="konin_kalisz")

# (10) At most one of Bytom, Sosnowiec and Katowice
m.addConstr(y_i["Bytom"] + y_i["Sosnowiec"] + y_i["Katowice"] <= 1, name="bytom_sosnowiec_katowice")

# (11) Wodzisław Śląski and Jastrzębie-Zdrój cannot both be included
m.addConstr(y_i["Wodzisław Śląski"] + y_i["Jastrzębie-Zdrój"] <= 1, name="wodzislaw_jastrzebie")

# (12) At least one of Poznań, Zielona Góra and Leszno
m.addConstr(y_i["Poznań"] + y_i["Zielona Góra"] + y_i["Leszno"] >= 1, name="poznan_zielona_leszno")

for k in K:
    # (13) A pair of cities can only be connected in one direction
    if USE_ONE_DIRECTION:
        for (i, j) in A_k[k]:
            if i < j:  # add each pair only once
                m.addConstr(x_ij[i, j] + x_ij[j, i] <= 1, name=f"one_direction_{i}_{j}")

    # (14) Subtour elimination: the next city in the route gets a higher position
    if USE_SUBTOUR_ELIMINATION:
        for (i, j) in A_k[k]:
            m.addConstr(u_i[j] >= u_i[i] + 1 - M_k[k] * (1 - x_ij[i, j]), name=f"subtour_{i}_{j}")

    # (15) The starting city has position 0
    m.addConstr(u_i[s_k[k]] == 0, name=f"order_start_{k}")

    # (16) Upper bound on the positions (lower bound 0 is set on the variable, (19))
    for i in V_k[k]:
        m.addConstr(u_i[i] <= M_k[k] - 1, name=f"order_bound_{i}")

# (17)-(19) are handled by the variable types and bounds above

# Solve the model
m.optimize()

if m.status == GRB.OPTIMAL:
    print(f"\nTotal cable built (including any loops): {m.ObjVal:.2f}")
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
    full_route = (
        routes[1]
        + routes[2]
        + routes[3]
    )

    print("\nThe cities connected by the main cable in order. Starting from Warsaw\n")
    print(" -> ".join(full_route))

    # Print routes distinguished by area
    print("\nRoutes sorted by area:\n")
    for k in K:
        print(f"Area {k}: {' -> '.join(routes[k])}")
        print(f"Length: {lengths[k]:.2f}\n")

    # Connections that are selected but not part of the route from start to end
    route_arcs = {
        (routes[k][n], routes[k][n + 1]) for k in K for n in range(len(routes[k]) - 1)
    }
    selected_arcs = [(i, j) for (i, j) in all_arcs if x_ij[i, j].X > 0.5]
    loose_arcs = [(i, j) for (i, j) in selected_arcs if (i, j) not in route_arcs]

    print("Connections not on the main cable (loops):\n")
    for (i, j) in loose_arcs:
        print(f"{i} -> {j}  (length {D_ij[i, j]:.2f})")
    if not loose_arcs:
        print("None")

    # Save every selected connection to results/c_broken_arcs.csv
    RESULTS_DIR.mkdir(exist_ok=True)

    city_area = {city: k for k in K for city in V_k[k]}

    with open(RESULTS_DIR / "c_broken_arcs.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["from", "to", "area", "length", "on_route", "two_way"])
        for (i, j) in selected_arcs:
            on_route = (i, j) in route_arcs
            two_way = x_ij[j, i].X > 0.5
            writer.writerow([i, j, city_area[i], round(D_ij[i, j], 3), on_route, two_way])

else:
    print("No optimal solution found.")
