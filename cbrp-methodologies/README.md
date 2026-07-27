# CBRP Methodologies — Prize-Collecting Dengue Arc Routing

Optimization methodologies for the **Census Block Routing Problem (CBRP)** applied to
dengue-control field operations. Given a road network whose street segments are grouped
into census **blocks**, each carrying a number of dengue **cases** (a prize) and a service
**time**, the goal is to build routes that maximize collected prizes subject to a global
time budge `T`.

The repository implements both **deterministic** and **two-stage stochastic** variants,
solved with **exact models** (Gurobi) and **(meta)heuristics**.

---

## Table of Contents

1. [Problem variants](#problem-variants)
2. [Repository layout](#repository-layout)
3. [Dependencies](#dependencies)
4. [Building](#building)
5. [Instance formats](#instance-formats)
6. [Executables and how to run them](#executables-and-how-to-run-them)
   - [Deterministic exact model (`cbrp-det`)](#1-deterministic-exact-model-cbrp-det)
   - [Greedy heuristic (`cbrp-det-greedy` / `cbrp-det-heur`)](#2-greedy-heuristic-cbrp-det-greedy--cbrp-det-heur)
   - [Lagrangean relaxation (`cbrp-det-lagr`)](#3-lagrangean-relaxation-cbrp-det-lagr)
   - [Stochastic exact model (`cbrp-stoc`)](#4-stochastic-exact-model-cbrp-stoc)
   - [Simulated Annealing for the stochastic problem (`cbrp-stoc-sa`)](#5-simulated-annealing-cbrp-stoc-sa)
   - [Simheuristic service (`cbrp-simheur`)](#6-simheuristic-service-cbrp-simheur)
7. [Batch experiments](#batch-experiments)
8. [Analysis notebooks](#analysis-notebooks)
9. [Preprocessing note](#preprocessing-note)

---

## Problem variants

| Dimension        | Options |
|------------------|---------|
| **Uncertainty**  | Deterministic · Two-stage stochastic (a first-stage route plus one second-stage route per scenario) |
| **Routing model**| `TRAIL` (each arc used at most once) · `WALK` (arcs may be traversed multiple times) |
| **Formulation**  | `EXP` (exponential, with subtour-elimination cuts added lazily in a callback) · `MTZ` (compact Miller–Tucker–Zemlin) |
| **Solver**       | Exact (Gurobi) · Greedy · Lagrangean relaxation · Simulated Annealing · Simheuristic |

In the stochastic model, `alpha` weights the trade-off between attending a block in the
first stage versus deferring it to the scenario-dependent second stage.

---

## Repository layout

```
src/
├── classes/        # Core data model: Graph, Input, Route, Scenario, Solution, Arc
├── common/         # ShortestPath, BlockConnection, Knapsack, Boost/Postgres helpers
├── exact/          # Gurobi models:
│                   #   DeterministicModel(.Walk), StochasticModel(.Walk),
│                   #   DeterministicModelWalkBarrierMethod
├── heuristic/      # GreedyHeuristic, Lagrangean, LocalSearch, WarmStart,
│   ├── metaheuristics/   #   SimulatedAnnealing
│   └── stochastic/       #   StartSolution, LocalSearch, SolutionPool, Utils
├── simheuristic/   # Simheuristic orchestration service
└── metrics/        # Metric computation utilities

main-deterministic-model.cpp   -> cbrp-det
main-det-greedy-heuristic.cpp  -> cbrp-det-greedy, cbrp-det-heur
main-lagrangean.cpp            -> cbrp-det-lagr
main-stochastic-model.cpp      -> cbrp-stoc
main-sa.cpp                    -> cbrp-stoc-sa
main-simheuristic.cpp          -> cbrp-simheur

instances/        # Input instances (see below)
script-execution.py  # Batch runner for all methodologies
analysis-*.ipynb     # Result analysis notebooks
```

---

## Dependencies

| Library | Purpose | Default discovery |
|---------|---------|-------------------|
| **CMake ≥ 3.10**, a **C++20** compiler | build | — |
| **Gurobi** | exact models | `$GUROBI_HOME` or `/opt/gurobi*/linux64` |
| **Boost** | graph utilities | `/opt/boost_*` or system |
| **LEMON** | max-flow / min-cut for fractional cuts | `/opt/lemon-*` |
| **libpqxx / libpq**, **ZeroMQ (libzmq)** | only for `cbrp-simheur` (Postgres + messaging) | system |

A valid Gurobi license is required to run any exact model (`cbrp-det`, `cbrp-stoc`,
`cbrp-det-lagr`). The heuristics (`cbrp-det-greedy`, `cbrp-det-heur`, `cbrp-stoc-sa`) do
**not** link against Gurobi.

---

## Building

```bash
# (optional) point CMake at your Gurobi install
export GUROBI_HOME=/opt/gurobi1100/linux64

cmake -S . -B build
cmake --build build -j$(nproc)
```

Binaries are produced inside `build/`. Build a single target with, e.g.:

```bash
cmake --build build --target cbrp-stoc -j$(nproc)
```

Available targets: `cbrp-det`, `cbrp-det-greedy`, `cbrp-det-heur`, `cbrp-det-lagr`,
`cbrp-stoc`, `cbrp-stoc-sa`, `cbrp-simheur`.

---

## Instance formats

**Graph file** (`instances/.../<name>.txt`) — first line `N M B` (number of nodes, arcs,
blocks), followed by node lines and arc lines:

```
117 336 52
N 0 -5.516019 -38.268638 31            # N <id> <lat> <lon> <comma-separated block ids>
N 1 -5.518938 -38.270743 49,32,41,0
...
A <origin> <destination> <length> <block>   # arc lines
```

**Scenario file** (`instances/.../scenarios-<name>.txt`) — used only by the stochastic
methodologies. First line is the number of scenarios `S`, then per-scenario probability
and per-block case counts:

```
50
P 0 0.020          # P <scenario> <probability>
B 0 1 1            # B <scenario> <block> <cases>
B 0 2 1
...
```

Instance folders:

| Folder | Contains | Used by |
|--------|----------|---------|
| `instances/cases-alto-santo`, `instances/cases-limoeiro` | graphs only | deterministic methods |
| `instances/simulated-alto-santo`, `instances/simulated-limoeiro` | graphs + `scenarios-*` | stochastic methods |
| `instances/test*` | small/diagnostic instances | testing |

> All examples below assume you run them from `build/` (so `./cbrp-...`) and reference
> instances with a relative path back to the repository root (`../instances/...`).
> The hardcoded time budget is `T = 1200` (and `alpha = 0.8` for the deterministic models).

---

## Executables and how to run them

### 1. Deterministic exact model (`cbrp-det`)

```
cbrp-det <graph> <formulation> <result_file> <routing> <preprocessing> <frac_cut> <warm_start>
```

| Arg | Meaning | Values |
|-----|---------|--------|
| `formulation` | model family | `MTZ` \| `EXP` |
| `routing` | route structure | `TRAIL` \| `WALK` |
| `preprocessing` | reduce graph to positive-case blocks | `0` \| `1` |
| `frac_cut` | add fractional (min-cut) cuts in the callback | `0` \| `1` |
| `warm_start` | seed the solver with a heuristic solution | `0` \| `1` |

Gurobi time limit: 3600 s.

```bash
cd build
# Exponential TRAIL formulation with preprocessing and fractional cuts
./cbrp-det ../instances/cases-alto-santo/alto-santo-500-1.txt \
           EXP result-det.txt TRAIL 1 1 0
```

### 2. Greedy heuristic (`cbrp-det-greedy` / `cbrp-det-heur`)

Both targets build from the same entry point and share the CLI:

```
cbrp-det-greedy <graph> <result_file> <preprocessing>
```

```bash
cd build
./cbrp-det-greedy ../instances/cases-limoeiro/limoeiro-500-1.txt result-greedy.txt 1
```

### 3. Lagrangean relaxation (`cbrp-det-lagr`)

```
cbrp-det-lagr <graph> <result_file> <preprocessing> <use_heuristic> <use_barrier_method>
```

| Arg | Meaning | Values |
|-----|---------|--------|
| `use_heuristic` | run the primal heuristic inside the relaxation | `0` \| `1` |
| `use_barrier_method` | solve subproblems with the barrier method | `0` \| `1` |

```bash
cd build
./cbrp-det-lagr ../instances/cases-alto-santo/alto-santo-500-1.txt \
                result-lagr.txt 1 1 0
```

### 4. Stochastic exact model (`cbrp-stoc`)

```
cbrp-stoc <graph> <scenarios> <result_file> <formulation> <routing> <alpha> <preprocessing> <frac_cut> <warm_start>
```

| Arg | Meaning | Values |
|-----|---------|--------|
| `formulation` | model family | `MTZ` \| `EXP` |
| `routing` | route structure | `TRAIL` \| `WALK` |
| `alpha` | first/second-stage weight | e.g. `0.8` |
| `preprocessing` / `frac_cut` / `warm_start` | as above | `0` \| `1` |

Gurobi time limit: 120 s.

```bash
cd build
# Exponential WALK stochastic model, alpha=0.8, preprocessing + fractional cuts
./cbrp-stoc ../instances/simulated-limoeiro/limoeiro-500-4.txt \
            ../instances/simulated-limoeiro/scenarios-limoeiro-500-4.txt \
            result-stoc.txt EXP WALK 0.8 1 1 0
```

### 5. Simulated Annealing (`cbrp-stoc-sa`)

```
cbrp-stoc-sa <graph> <scenarios> <result_file> <alpha> <temperature> <temperature_max> \
             <alpha_sa> <max_iters> <delta_type> <first_improve> <preprocessing>
```

| Arg | Meaning | Example |
|-----|---------|---------|
| `temperature` / `temperature_max` | SA initial / max temperature | `1.0` / `100` |
| `alpha_sa` | cooling factor | `1.05` |
| `max_iters` | iterations per temperature level | `100` |
| `delta_type` | perturbation intensity | `moderate` |
| `first_improve` | first-improvement local search | `0` \| `1` |
| `preprocessing` | per-scenario graph reduction | `0` \| `1` |

```bash
cd build
./cbrp-stoc-sa ../instances/simulated-limoeiro/limoeiro-500-4.txt \
               ../instances/simulated-limoeiro/scenarios-limoeiro-500-4.txt \
               result-sa.txt 0.8 1.0 100 1.05 100 moderate 0 1
```

### 6. Simheuristic service (`cbrp-simheur`)

A long-running service that combines simulation with the heuristics and talks to a
Postgres database / ZeroMQ endpoint.

```
cbrp-simheur <graph> <T> <alpha> <connection_address>
```

```bash
cd build
./cbrp-simheur ../instances/simulated-alto-santo/alto-santo-500-1.txt \
               1200 0.8 "tcp://127.0.0.1:5555"
```

---

## Batch experiments

`script-execution.py` enumerates parameter grids and runs the binaries in parallel,
writing one result file per instance into per-experiment folders. **Run it from `build/`**
(where the binaries live):

```bash
cd build
cp ../script-execution.py .
ln -s ../instances instances     # so relative instance paths resolve

python script-execution.py SA       # Simulated Annealing       -> stochastic-results-sa/
python script-execution.py MODEL    # Stochastic exact model    -> stochastic-results-model/
python script-execution.py DET      # Deterministic exact model -> deterministic-results/
python script-execution.py GREEDY   # Greedy heuristic          -> deterministic-results-greedy/
python script-execution.py LAGR     # Lagrangean relaxation     -> deterministic-results-lagrangean/
```

Heuristic modes (`SA`, `GREEDY`, `LAGR`) run with a process pool (default 6 workers);
exact modes (`MODEL`, `DET`) run sequentially.

---

## Analysis notebooks

Result folders are post-processed by the Jupyter notebooks at the repository root:

- `analysis-stochastic-model.ipynb` — TRAIL/WALK × MTZ/EXP bounds, gaps, runtimes.
- `analysis-simulated-annealing.ipynb` — SA parameter sweeps and LB comparisons.
- `analysis-deterministic-model.ipynb`, `analysis-greedy.ipynb`, `analysis-lagrangean.ipynb`.

`analysis_utils.py` holds shared parsing/plotting helpers.

---

## Preprocessing note

With `preprocessing = 1`, the graph is reduced to blocks that carry positive cases and,
for the stochastic methods, the `Input` builds **S + 1 independent graphs**: one for the
first stage plus one reduced graph per scenario (containing only that scenario's active
blocks and the shortest paths connecting them). Block IDs are kept consistent across all
graphs; node IDs are renumbered compactly per scenario. With `preprocessing = 0`, a single
shared graph is used for every stage, reproducing the original behavior.
