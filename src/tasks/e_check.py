"""Validate copper results from raw inputs; does not import the optimization model.
This checker was written with knowledge of the formulation, so its generation
must not be described as blind independent AI verification in the report.
"""
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent



# Read city data and the fixed main route
with open(ROOT / 'data/cities.csv', encoding='utf-8-sig') as f:
    cities = {r['city']: r for r in csv.DictReader(f)}
with open(ROOT / 'results/c_solution.csv', encoding='utf-8-sig') as f:
    main_route = {r['city'] for r in csv.DictReader(f)}
params = json.loads((ROOT / 'data/copper_parameters.json').read_text())
stations = params['stations']
remaining = cities.keys() - main_route
with open(ROOT / 'results/e_solution.csv', encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
expected = {(i, s) for i in remaining for s in stations}
pairs = [(r['city'], r['station']) for r in rows]
errors = []
if len(pairs) != len(set(pairs)) or set(pairs) != expected:
    raise ValueError('Missing, duplicate, or unexpected city-station pairs')
totals = {i: 0.0 for i in remaining}
station_totals = {s: 0.0 for s in stations}
total_cost = 0.0
tol = 1e-5
for r in rows:
    i, s = r['city'], r['station']
    f = float(r['capacity_tbps'])
    d = math.hypot(float(cities[i]['x']) - float(cities[s]['x']), float(cities[i]['y']) - float(cities[s]['y']))
    upper = max(0, min(params['max_cable_tbps'], 2 * math.pi * min(params['distance_plateau'], params['distance_cutoff'] - d)))
    q = float(cities[i]['demand_tbps'])
    if not math.isfinite(f) or f < -tol or f > upper + tol:
        errors.append(f'Invalid cable capacity: {i} -> {s}')
    if i == 'Łódź' and f > params['lodz_max_share'] * q + tol:
        errors.append(f'Łódź share exceeded at {s}')
    cost = params['cost_eur_per_length_tbps'] * d * f
    if abs(float(r['distance']) - d) > tol or abs(float(r['max_capacity_tbps']) - upper) > tol or abs(float(r['demand_tbps']) - q) > tol or abs(float(r['cost_eur']) - cost) > 0.01:
        errors.append(f'Incorrect exported data: {i} -> {s}')
    totals[i] += f
    station_totals[s] += f
    total_cost += cost
for i, value in totals.items():
    if abs(value - float(cities[i]['demand_tbps'])) > tol:
        errors.append(f'Demand not met: {i}')
for s, value in station_totals.items():
    if value > stations[s] + tol:
        errors.append(f'Station capacity exceeded: {s}')
summary = json.loads((ROOT / 'results/e_summary.json').read_text())
if abs(summary['total_cost_eur'] - total_cost) > 0.01:
    errors.append('Summary cost mismatch')
if errors:
    raise ValueError('\n'.join(errors))
print(f'PASS: {len(remaining)} city demands, {len(rows)} cable bounds, all station capacities, Łódź shares, and total cost EUR {total_cost:,.2f}')
