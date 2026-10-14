"""Task f: demand scenarios and simultaneous RHS sensitivity for pi."""
import csv
import json
import math
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
#Read inputs
with open(ROOT / "data/cities.csv", encoding="utf-8-sig") as f:
    cities = list(csv.DictReader(f))
with open(RESULTS_DIR / "c_solution.csv", encoding="utf-8-sig") as f:
    route = {r["city"] for r in csv.DictReader(f)}
with open(ROOT / "data/copper_parameters.json", encoding="utf-8") as f:
    parameters = json.load(f)

#Sets and parameters
N = [r["city"] for r in cities if r["city"] not in route]
S = list(parameters["stations"])
q_i = {r["city"]: float(r["demand_tbps"]) for r in cities if r["city"] in N}
coordinates = {r["city"]: (float(r["x"]), float(r["y"])) for r in cities}
D_is = {(i, s): math.dist(coordinates[i], coordinates[s]) for i in N for s in S}
E = [(i, s) for i in N for s in S if D_is[i, s] < parameters["distance_cutoff"]]
a_is = {(i, s): min(parameters["distance_plateau"], parameters["distance_cutoff"] - D_is[i, s]) for i, s in E}

#Keep the constant and distance-dependent cable limits separate.
#This equivalent formulation makes all changing RHS values linear in pi.
m = gp.Model("task_f")
m.Params.OutputFlag = 0
m.Params.Method = 0  #Primal simplex returns a basic solution
f_is = m.addVars(E, lb=0, name="f")
for n, pair in enumerate(E):
    f_is[pair].VarName = f"f_{n}"
m.setObjective(parameters["cost_eur_per_length_tbps"] * gp.quicksum(D_is[i, s] * f_is[i, s] for i, s in E), GRB.MINIMIZE)
for i in N:
    m.addConstr(gp.quicksum(f_is[i, s] for s in S if (i, s) in E) == q_i[i], name="demand_Konin" if i == "Konin" else f"demand_{N.index(i)}")
for s in S:
    m.addConstr(gp.quicksum(f_is[i, s] for i in N if (i, s) in E) <= parameters["stations"][s], name=f"station_{s}")
distance_constraints = []
for i, s in E:
    m.addConstr(f_is[i, s] <= parameters["max_cable_tbps"], name=f"cable_{N.index(i)}_{S.index(s)}")
    constraint = m.addConstr(f_is[i, s] <= 2 * math.pi * a_is[i, s], name=f"distance_{N.index(i)}_{S.index(s)}")
    distance_constraints.append((constraint, 2 * a_is[i, s]))
    if i == "Łódź":
        m.addConstr(f_is[i, s] <= parameters["lodz_max_share"] * q_i[i], name=f"lodz_{s}")
m.optimize()
if m.Status != GRB.OPTIMAL:
    raise RuntimeError("Baseline is not optimal")

#Save baseline sensitivity information before changing demand
baseline_cost = m.ObjVal
variables = m.getVars()
constraints = m.getConstrs()
variable_basis = m.getAttr("VBasis", variables)
constraint_basis = m.getAttr("CBasis", constraints)
m.write(str(RESULTS_DIR / "f_baseline.bas"))
konin = m.getConstrByName("demand_Konin")
shadow_price = konin.Pi
rhs_min, rhs_max = konin.SARHSLow, konin.SARHSUp

#Part 1: calculate the allowable pi interval from the baseline basis.
A = m.getA().toarray()
columns = []
names = []
for j, status in enumerate(variable_basis):
    if status == 0:
        columns.append(A[:, j])
        names.append(variables[j].VarName)
for j, status in enumerate(constraint_basis):
    if status == 0:
        column = np.zeros(len(constraints))
        column[j] = 1  #All inequality constraints in this model use <=
        columns.append(column)
        names.append("slack_" + constraints[j].ConstrName)
B = np.column_stack(columns)
if B.shape != (len(constraints), len(constraints)):
    raise RuntimeError("Unexpected basis size")
b = np.array([c.RHS for c in constraints])
h = np.zeros(len(constraints))
for constraint, slope in distance_constraints:
    h[constraint.index] = slope
#Basic capacities and slacks: x(pi) = x0 + (pi - baseline_pi) * direction
x0 = np.linalg.solve(B, b)
direction = np.linalg.solve(B, h)
if np.max(np.abs(B @ x0 - b)) > 1e-7 or x0.min() < -1e-6:
    raise RuntimeError("Invalid reconstructed baseline basis")
#All nonbasic structural variables/slacks are zero; all variables have lower
#bound zero and no finite upper bound in this formulation.
lower_delta, upper_delta = -math.pi, math.inf
lower_name, upper_name = "pi_nonnegative", None
for name, value, slope in zip(names, x0, direction):
    if slope > 1e-8:
        bound = -max(0, value) / slope
        if bound > lower_delta:
            lower_delta, lower_name = bound, name
    elif slope < -1e-8:
        bound = -max(0, value) / slope
        if bound < upper_delta:
            upper_delta, upper_name = bound, name
pi_min, pi_max = math.pi + lower_delta, math.pi + upper_delta

#Part 2: change Konin's demand and solve the four scenarios.
#Konin: change only its demand and re-solve each scenario.
scenario_rows = []
for change in [-0.2, -0.1, 0, 0.1, 0.2]:
    demand = q_i["Konin"] * (1 + change)
    konin.RHS = demand
    m.optimize()
    if m.Status != GRB.OPTIMAL:
        raise RuntimeError(f"Scenario {change} is not optimal")
    prediction = baseline_cost + shadow_price * (demand - q_i["Konin"])
    scenario_rows.append([
        100 * change, demand, m.ObjVal, m.ObjVal - baseline_cost,
        100 * (m.ObjVal - baseline_cost) / baseline_cost,
        rhs_min - 1e-7 <= demand <= rhs_max + 1e-7, prediction,
    ])
with open(RESULTS_DIR / "f_konin.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["demand_change_pct", "demand_tbps", "cost_eur", "cost_change_eur", "cost_change_pct", "within_baseline_rhs_range", "shadow_price_prediction_eur"])
    writer.writerows(scenario_rows)

#Save the sensitivity results
summary = dict(
    baseline_cost_eur=baseline_cost, konin_shadow_price_eur_per_tbps=shadow_price,
    konin_allowable_demand_min=rhs_min, konin_allowable_demand_max=rhs_max,
    pi_baseline=math.pi, pi_min=pi_min, pi_max=pi_max,
    lower_limiting_variable=lower_name, upper_limiting_variable=upper_name,
    formulation="Separate 200 TB/s and distance limits; baseline primal simplex basis saved in f_baseline.bas",
)
with open(RESULTS_DIR / "f_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)
print(f"Konin shadow price: EUR {shadow_price:,.3f}/TB/s; demand range [{rhs_min:.6f}, {rhs_max:.6f}]")
for row in scenario_rows:
    print(f"Demand {row[0]:+.0f}%: {row[1]:.1f} TB/s; cost EUR {row[2]:,.2f}; change EUR {row[3]:+,.2f}")
print(f"Baseline basis remains optimal for pi in [{pi_min:.9f}, {pi_max:.9f}]")
print(f"Limiting variables: {lower_name}, {upper_name}")
