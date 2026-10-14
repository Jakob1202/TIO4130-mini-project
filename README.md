# TIO4130 Mini Project – A Communication Problem

Optimization models for the MobiPhlex case, written in Python with Gurobi.
The project has three parts:

- **Task c (main cable):** an integer linear program that finds the cheapest main
  cable from Warszawa to Jelenia Góra through three areas of Poland, while
  meeting the geographical and governmental requirements.
- **Tasks d/e (copper cables):** a continuous linear program that connects the
  cities not on the main line to the switching stations in Warszawa, Kielce and
  Opole. It meets each city's demand at the lowest cable cost, within the limits
  on station capacity, cable capacity, cable length and the 40% rule for Łódź.
- **Task f (sensitivity analysis):** how the copper cost changes if Konin's
  demand is off by 10% or 20%, and the interval for π in which the current basis
  stays optimal.

## Project structure

```
TIO-4130-mini-project/
├── Mini project 2026 - A communication problem.pdf   # The case description
├── README.md
├── requirements.txt              # Python packages used by the project
└── src/
    ├── data/
    │   ├── cities.csv                  # Area, city, coordinates (x, y) and demand (TB/s) for each city
    │   ├── main_cable_parameters.json  # Task 1: start/end city and minimum cities per area, government rules, cable cost
    │   └── copper_parameters.json      # Task 2: station capacities, cable price and cable limits
    ├── tasks/
    │   ├── 1/                          # Task 1: main cable (task a, b, and c)
    │   │   ├── c_model.py              # The mathematical model for the main cable
    │   │   ├── c_visualize.py          # Draws the route from c_solution.csv on a map
    │   │   ├── c_check.py              # Independent checker of c_solution.csv against the case
    │   │   ├── c_model_broken.py       # The model without constraint (13), to show what it does
    │   │   └── c_visualize_broken.py   # Draws every connection from c_broken_arcs.csv on a map
    │   └── 2/                          # Task 2: copper cables (task d, e, and f)
    │       ├── e_model.py              # The copper connection model
    │       ├── e_visualize.py          # Draws the copper cables per station
    │       ├── e_check.py              # Independent checker of the copper results against the case
    │       ├── e_visualize_combined.py # Draws the main line and all copper cables on one map
    │       └── f_sensitivity.py        # Konin demand scenarios and the interval for π
    ├── results/
    │   ├── 1/
    │   │   ├── c_solution.csv          # Route found by the model (order, area, city, x, y)
    │   │   ├── c_map.png               # Map of the route
    │   │   ├── c_check_output.png      # Output of c_check.py, used in the report
    │   │   ├── c_broken_arcs.csv       # Every connection chosen by the broken model (from, to, area, length, on_route, two_way)
    │   │   └── c_broken_map.png        # Map of the broken model's solution, with loops in red
    │   └── 2/
    │       ├── e_solution.csv          # Capacity and cost for every city-station pair
    │       ├── e_stations.csv          # Capacity used at each switching station
    │       ├── e_summary.json          # Total cost and number of cables
    │       ├── e_duals.csv             # Dual values, slacks and RHS ranges
    │       ├── e_map.png               # One panel per station with cable capacities
    │       ├── e_combined_map.png      # Main line and all copper cables on one map
    │       ├── f_konin.csv             # Cost for each Konin demand scenario
    │       ├── f_summary.json          # Konin shadow price and range, interval for π
    │       └── f_baseline.bas          # Optimal basis of the copper model
    └── archive/                        # Work not currently in use
```

All data is read from files in `src/data/`, so the models contain no case data.
Scripts and results are split by the two tasks in the report: folder `1` holds
the main cable (task c) and folder `2` the copper cables and the sensitivity
analysis (tasks e and f). Task 2 reads the main line from `results/1/c_solution.csv`,
so run task 1 first.

The demand column in `cities.csv` is only used in task 2.

The scripts find `data/` and `results/` relative to their own location, so
they can be run from any folder.

## Setting up the virtual environment

The project uses a virtual environment in `.venv` so that everyone runs the
same Python and packages. This requires Python 3.13 (other recent versions should
also work).

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run `source .venv/bin/activate` again each time you open a new terminal. When
the environment is active, the terminal prompt starts with `(.venv)`. Type
`deactivate` to leave it.

In VS Code, select the interpreter `.venv/bin/python`
(Cmd+Shift+P → "Python: Select Interpreter") so the Run button uses the
same environment.

Gurobi installed through pip comes with a restricted license that is enough
for these models. For larger models, a free academic license can be obtained
from gurobi.com.

## Running task c

From the project root, with the environment active:

```bash
python src/tasks/1/c_model.py       # Solve the model and save results/1/c_solution.csv
python src/tasks/1/c_visualize.py   # Draw the route and save results/1/c_map.png
python src/tasks/1/c_check.py       # Check the solution against every requirement in the case
```

Run `c_model.py` first, since the other two read the solution file it
creates.

The model reads the city data from `cities.csv` and everything else from
`main_cable_parameters.json`:

- `areas`: for each area, the start city, the end city and the minimum number of
  intermediate cities.
- `city_constraints`: the government rules. Each rule lists some cities, a sense
  (`<=`, `>=` or `==`) and a right-hand side, and becomes the constraint
  "sum of the selected cities (sense) right-hand side". Rules can be added or
  changed here without touching the code.
- `cost_per_length`: the cable cost per unit of length.

`c_check.py` was written from the case text and the format of `c_solution.csv`
only, so it has the case requirements written into the script instead of
reading them from `main_cable_parameters.json`.

### Broken model

`c_model_broken.py` is a copy of the model where the constraint that stops two
cities from being connected in both directions (13) is removed. Without it, the
model builds small two-city loops away from the main cable. Setting
`USE_ONE_DIRECTION = True` at the top of the file puts the constraint back. It
reads the same data files as `c_model.py`.

```bash
python src/tasks/1/c_model_broken.py       # Solve the broken model and save results/1/c_broken_arcs.csv
python src/tasks/1/c_visualize_broken.py   # Draw every selected connection and save results/1/c_broken_map.png
```

The broken model saves to its own files, so it does not overwrite the
results from `c_model.py`.

## Running the copper connection model (tasks d and e)

Task d is the mathematical formulation; task e is its implementation. The
model reads `src/data/cities.csv`, `src/data/copper_parameters.json`, and the
fixed main route in `src/results/1/c_solution.csv`, so run `c_model.py` first.

```bash
python src/tasks/2/e_model.py              # Solve and export capacities, costs and dual values
python src/tasks/2/e_check.py              # Check the results against every requirement in the case
python src/tasks/2/e_visualize.py          # Save the capacity map per station (results/2/e_map.png)
python src/tasks/2/e_visualize_combined.py # Save the combined map (results/2/e_combined_map.png)
```

Results are saved separately from the main cable results:

- `e_solution.csv`: all city-station pairs, distances, demands, cable bounds,
  installed capacities, and costs, including zero-capacity connections.
- `e_stations.csv`: station capacities, utilized capacities, and percentages.
- `e_summary.json`: total cost and number of positive cables.
- `e_duals.csv`: constraint shadow prices, slacks, and individual RHS sensitivity
  ranges.
- `e_map.png`: three station panels showing the fixed main route and copper
  cable capacities in TB/s.
- `e_combined_map.png`: the main line and all copper cables on one map.

`e_check.py` was written from the case text and the format of the result files
only, and does not import the model. It copies the coordinates and demands from
Table 1 of the case text, so it also checks `cities.csv` against the case. It
prints PASS/FAIL for each requirement, the answers to the questions in task e,
and exits with status 1 if any check fails.

## Running the sensitivity analysis (task f)

```bash
python src/tasks/2/f_sensitivity.py   # Konin demand scenarios and the interval for π
```

The script builds the copper model again from the same data files and saves:

- `f_konin.csv`: total cost when Konin's demand is changed by ±10% and ±20%,
  compared with the prediction from the shadow price.
- `f_summary.json`: the baseline cost, Konin's shadow price and allowable demand
  range, and the interval for π in which the current basis stays optimal.
- `f_baseline.bas`: the optimal basis of the baseline model.
