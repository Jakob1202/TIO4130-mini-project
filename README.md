# TIO4130 Mini Project – A Communication Problem

Python + Gurobi code for the MobiPhlex case. The tasks are described in
`Mini project 2026 - A communication problem.pdf`.

## Project structure

```
src/
├── data/            # All input data (the models contain no case data)
├── tasks/
│   ├── 1/           # Task 1: main cable (tasks a, b, c)
│   └── 2/           # Task 2: copper cables (tasks d, e, f)
├── results/
    ├── 1/           # Output from tasks/1
    └── 2/           # Output from tasks/2
```

## Setup

Requires Python 3.13.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The pip version of Gurobi includes a restricted license that is enough for these models.

## Running

Run from the project root with the environment active. All paths below are
relative to `src/`. Each script needs the files in its "Reads" column, so run
the scripts in the order listed. Task 2 uses the main line from task 1, so run
`c_model.py` first.

### Task 1

```bash
python src/tasks/1/c_model.py
python src/tasks/1/c_visualize.py
python src/tasks/1/c_check.py
python src/tasks/1/c_model_broken.py
python src/tasks/1/c_visualize_broken.py
```

| Script | Does | Reads | Writes to `results/1/` |
|---|---|---|---|
| `c_model.py` | Solves the main cable model | `data/cities.csv`, `data/main_cable_parameters.json` | `c_solution.csv` |
| `c_visualize.py` | Draws the route on a map | `data/cities.csv`, `results/1/c_solution.csv` | `c_map.png` |
| `c_check.py` | Independent checker of the route | `data/cities.csv`, `results/1/c_solution.csv` | – (prints PASS/FAIL) |
| `c_model_broken.py` | Solves the model without constraint (13) | `data/cities.csv`, `data/main_cable_parameters.json` | `c_broken_arcs.csv` |
| `c_visualize_broken.py` | Draws all selected connections, loops in red | `data/cities.csv`, `results/1/c_broken_arcs.csv` | `c_broken_map.png` |

### Task 2

```bash
python src/tasks/2/e_model.py
python src/tasks/2/e_check.py
python src/tasks/2/e_visualize.py
python src/tasks/2/e_visualize_combined.py
python src/tasks/2/f_sensitivity.py
```

| Script | Does | Reads | Writes to `results/2/` |
|---|---|---|---|
| `e_model.py` | Solves the copper model; saves capacities, station use and duals | `data/cities.csv`, `data/copper_parameters.json`, `results/1/c_solution.csv` | `e_solution.csv`, `e_stations.csv`, `e_duals.csv`, `e_summary.json` |
| `e_check.py` | Independent checker of the copper solution | `data/cities.csv`, `results/1/c_solution.csv`, `results/2/e_solution.csv`, `e_stations.csv`, `e_summary.json` | – (prints PASS/FAIL) |
| `e_visualize.py` | Draws the cables with capacities, one panel per station | `data/cities.csv`, `results/1/c_solution.csv`, `results/2/e_solution.csv` | `e_map.png` |
| `e_visualize_combined.py` | Draws the main line and all cables on one map | `data/cities.csv`, `results/1/c_solution.csv`, `results/2/e_solution.csv` | `e_combined_map.png` |
| `f_sensitivity.py` | Konin demand scenarios and the interval for π | `data/cities.csv`, `data/copper_parameters.json`, `results/1/c_solution.csv` | `f_konin.csv`, `f_summary.json`, `f_baseline.bas` |
