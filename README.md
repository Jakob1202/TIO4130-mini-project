# TIO4130 Mini Project – A Communication Problem

Optimization models for the MobiPhlex case, written in Python with Gurobi.
The project has two parts:

- **Task c (main cable):** an integer linear program that finds the cheapest main
  cable from Warszawa to Jelenia Góra through three areas of Poland, while
  meeting the geographical and governmental requirements.
- **Tasks d/e (copper cables):** a continuous linear program that connects the
  cities not on the main line to the switching stations in Warszawa, Kielce and
  Opole. It meets each city's demand at the lowest cable cost, within the limits
  on station capacity, cable capacity, cable length and the 40% rule for Łódź.

## Project structure

```
TIO-4130-mini-project/
├── Mini project 2026 - A communication problem.pdf   # The case description
├── README.md
├── requirements.txt              # Python packages used by the project
└── src/
    ├── data/
    │   └── cities.csv            # Area, city, coordinates (x, y) and demand (TB/s) for each city
    ├── results/
    │   ├── c_solution.csv        # Route found by the model in task c (order, area, city, x, y)
    │   ├── c_map.png             # Map of the route in task c
    │   ├── c_broken_arcs.csv     # Every connection chosen by the broken model (from, to, area, length, on_route, two_way)
    │   └── c_broken_map.png      # Map of the broken model's solution, with loops in red
    └── tasks/
        ├── c_model.py            # Task c: the mathematical model for the main cable
        ├── c_visualize.py        # Task c: draws the route from c_solution.csv on a map
        ├── c_check.py            # Task c: independent checker of c_solution.csv against the case
        ├── c_model_broken.py     # Task c: the model without constraints (13) and (14), to show what they do
        └── c_visualize_broken.py # Task c: draws every connection from c_broken_arcs.csv on a map
```

The demand column in `cities.csv` is only used in task d.

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
python src/tasks/c_model.py       # Solve the model and save results/c_solution.csv
python src/tasks/c_visualize.py   # Draw the route and save results/c_map.png
python src/tasks/c_check.py       # Check the solution against every requirement in the case
```

Run `c_model.py` first, since the other two read the solution file it
creates.

### Broken model

`c_model_broken.py` is a copy of the model where the constraint that stops two
cities from being connected in both directions (13) is removed. The subtour
constraint (14) is removed too, since it also blocks two-way connections. Without
both, the model builds small loops away from the main cable. The switches
`USE_ONE_DIRECTION` and `USE_SUBTOUR_ELIMINATION` at the top of the file put the
constraints back.

```bash
python src/tasks/c_model_broken.py       # Solve the broken model and save results/c_broken_arcs.csv
python src/tasks/c_visualize_broken.py   # Draw every selected connection and save results/c_broken_map.png
```

The broken model saves to its own files, so it does not overwrite the
results from `c_model.py`.

## Running the copper connection model (tasks d and e)

Task d is the mathematical formulation; task e is its implementation. The
model reads `src/data/cities.csv`, `src/data/copper_parameters.json`, and the
fixed main route in `src/results/c_solution.csv`.

```bash
python src/tasks/e_model.py       # Solve and export capacities, costs, and dual values
python src/tasks/e_check.py       # Validate saved capacities against the input data
python src/tasks/e_visualize.py   # Save the capacity map without opening a window
```

Results are saved separately from the main cable results:

- `e_solution.csv`: all city-station pairs, distances, demands, cable bounds,
  installed capacities, and costs, including zero-capacity connections.
- `e_stations.csv`: station capacities, utilized capacities, and percentages.
- `e_summary.json`: total cost and number of positive cables.
- `e_duals.csv`: constraint shadow prices, slacks, and individual RHS sensitivity
  ranges. These ranges alone do not establish the simultaneous allowable interval
  for pi requested in task f.
- `e_map.png`: three station panels showing the fixed main route and copper
  cable capacities in TB/s.

The checker does not import the model and recalculates distances and bounds.
It was generated with knowledge of the formulation, so it must not be described
as an AI checker written without seeing the model. Task e also requires your
own explanation using dual values before asking AI to evaluate that explanation.
