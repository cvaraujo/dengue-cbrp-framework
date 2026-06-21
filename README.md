## Table of contents

- [Architecture overview](#architecture-overview)
- [Complete code flow](#complete-code-flow)
  - [A. Simheuristic flow](#a-simheuristic-flow-optimization--simulation)
  - [B. Simulation-only flow](#b-simulation-only-flow-validation)
- [Directory structure](#directory-structure)
- [Prerequisites](#prerequisites)
- [How to run](#how-to-run)
  - [1. Simheuristic (optimization + simulation)](#1-simheuristic-optimization--simulation)
  - [2. Simulation only](#2-simulation-only)
- [Main parameters](#main-parameters)
- [Generated outputs](#generated-outputs)

---

## Architecture overview

Three processes cooperate at runtime, communicating through **sockets** and a shared **PostgreSQL/PostGIS** database:

```
                 ┌─────────────────────────────────────────────────────────┐
                 │                  Python orchestration                     │
                 │                                                           │
                 │   src/main-simheuristic.py   |   src/main.py             │
                 │   (simheuristic)             |   (simulation only)       │
                 └───────┬───────────────────────────┬─────────────────────┘
                         │                            │
        WebSocket (ws)   │                            │  WebSocket (ws)
        port 6868        │                            │  port 6868
                         ▼                            ▼
              ┌─────────────────────┐      ┌────────────────────────┐
              │   GAMA headless     │      │   GAMA headless         │
              │ dengue_propagation  │      │  dengue_propagation     │
              │      .gaml          │      │       .gaml             │
              └──────────┬──────────┘      └───────────┬────────────┘
                         │                             │
              ZeroMQ (REQ/REP)                         │
              tcp://...:2021                           │
                         ▼                             ▼
              ┌─────────────────────┐      ┌────────────────────────┐
              │  C++ optimizer      │      │   (not used here)       │
              │   cbrp-simheur      │      └────────────────────────┘
              └─────────────────────┘
                         │
                         ▼
        ┌──────────────────────────────────────────────┐
        │      PostgreSQL + PostGIS (dengue-propagation) │
        │  people / mosquitoes / breeding_sites / eggs / │
        │  metrics_infected_people / solutions ...       │
        └──────────────────────────────────────────────┘
```

| Component | Technology | Role |
|-----------|-----------|------|
| Orchestrator | Python | Builds the instance (OSM map → graph), generates the initial scenario, coordinates simulation and optimization, computes metrics. |
| Simulation | GAMA (GAML) | Propagates dengue over a horizon of cycles and writes new cases to `metrics_infected_people`. |
| Optimization | C++ (`cbrp-simheur`) | Receives the graph (`graph.txt`) and returns the set of blocks to fumigate. |
| Persistence | PostgreSQL + PostGIS | Agent state, real cases (SINAN), and simulation results. |

---

## Complete code flow

### A. Simheuristic flow (optimization + simulation)

Entry point: **`src/main-simheuristic.py`** → class **`SimheuristicFramework`** (`src/use_cases/optimization/simheuristic.py`).

```
main-simheuristic.py
   │  (reads arguments: mode, city, map, dates, alpha, time, elite, iterations)
   ▼
run_single_experiment()
   ├─ Simulation(server_path, port, model)        # starts/connects to GAMA headless
   └─ SimheuristicFramework(...).run(socket_str, max_time, elite_size, max_iters)
        │
        ├─ 1. _create_base_environment()
        │       ├─ clear_database()
        │       ├─ OpenStreetMap(city, map_size)            # downloads the OSM map
        │       ├─ MapAdapter.convert_osm_to_graph()        # OSM → Graph (nodes/arcs/blocks)
        │       ├─ get_notifications_between_dates()         # real SINAN cases (PostGIS)
        │       ├─ get_infected_recovered_people_per_block() # real cases per block
        │       ├─ _compute_valid_block_mask()               # discards degenerate blocks
        │       ├─ _write_graph("graph.txt")                 # instance for the C++ optimizer
        │       ├─ ScenarioGeneration.create_starting_scenario()  # populate people/mosquitoes/breeding sites in DB
        │       ├─ export_osm_to_shapefile()                 # shapefiles for GAMA
        │       └─ _call_simulation(max_cycles=0)            # loads the initial scenario into GAMA
        │
        ├─ 2. _start_optimization_executable()
        │       └─ cmake + make cbrp-simheur; starts the binary listening on ZeroMQ (port 2021)
        │
        ├─ 3. _compute_start_scenarios()
        │       └─ _call_simulation(max_cycles=14, batch)    # generates initial stochastic scenarios
        │       └─ _get_scenario_cases_per_block()           # simulated cases per block/scenario
        │
        ├─ 4. start_solution = _call_optimization("load" → "run")  # first optimizer solution
        │       └─ _evaluate_deterministic_solution()        # deterministic + stochastic OF
        │
        ├─ 5. LOOP until max_time_seconds:
        │       ├─ _call_optimization("run")                 # new candidate solution
        │       ├─ _evaluate_deterministic_solution()        # uses surrogate model (cached scenarios)
        │       │     └─ every max_iters: runs a new short simulation to refresh scenarios
        │       └─ keeps an "elite" pool of the best stochastic solutions (heap)
        │
        ├─ 6. _call_optimization("stop")
        │
        └─ 7. risk_naive_analysis()
                ├─ Baseline (no intervention)                # 14-cycle simulation
                ├─ "Naive" solution (greedy by cases)        # fumigation simulation
                ├─ Each elite solution                        # fumigation simulation
                ├─ risk_naive_analysis_boxplot.png/.pdf
                ├─ risk_naive_analysis_stats.csv
                └─ _generate_debug_report() → debug_report.html
```

**Conceptual summary:** the optimizer proposes *which blocks to fumigate*; the simulation evaluates the *stochastic impact* of those blocks on future cases; the simheuristic iterates between the two, using a *surrogate model* (cached simulated scenarios) to speed up evaluation and periodically refreshing those scenarios.

### B. Simulation-only flow (validation)

Entry point: **`src/main.py`** → uses **`SimulationMetrics`** (`src/use_cases/simulation_metrics.py`). Here there is **no C++ optimizer**: the goal is to validate the simulation by comparing simulated vs. real cases.

```
main.py <output_folder> <prev_date> <start_date>
   │
   ├─ OpenStreetMap + convert_osm_to_graph()            # map → graph
   ├─ get_notifications_between_dates()                  # real cases (SINAN)
   ├─ SimulationMetrics.compare_simulated_with_real_cases()
   │      ├─ clear_database()
   │      ├─ ScenarioGeneration.create_starting_scenario()   # initial scenario in DB
   │      ├─ export_osm_to_shapefile()
   │      ├─ Simulation().run_simulation(max_cycles=0)        # loads scenario
   │      ├─ Simulation().run_simulation(max_cycles=180, batch) # runs long horizon
   │      └─ plot_min_max_avg_real()                          # simulated vs real cases per week
   │           ├─ <...>.csv  / <...>_quality_metrics.csv      # Pearson, MAE, endemic channel
   │           └─ <...>.pdf                                   # chart
   └─ per-block metrics → block_infected_proportions.txt
```

Both flows share the same building blocks: `OpenStreetMap`/`MapAdapter` (map→graph), `ScenarioGeneration` (initial scenario in the DB), `Simulation` (WebSocket bridge to GAMA), and the `PostgreSQLAdapter`.

---

## Directory structure

```
dengue-cbrp-framework/
├── src/
│   ├── main-simheuristic.py        # entry point: simheuristic (single/batch)
│   ├── main.py                     # entry point: simulation only + validation
│   ├── domain/                     # Graph, Node, Arc, OSM, utils...
│   ├── adapters/
│   │   ├── osm/map_adapter.py      # OSM → Graph, shapefiles
│   │   ├── sql/postgree.py         # PostgreSQLAdapter + queries
│   │   └── json/json_adapter.py    # parameters → GAMA payload
│   └── use_cases/
│       ├── optimization/simheuristic.py   # SimheuristicFramework (core)
│       ├── simulation.py                  # WebSocket bridge to GAMA headless
│       ├── simulation_metrics.py          # sim vs real validation
│       ├── scenario_generation.py         # creates the initial scenario in DB
│       └── deterministic_instance.py      # instance generation
├── simulation/
│   ├── models/dengue_propagation.gaml     # MABS model (headless experiments)
│   └── data/script.sql                    # database schema + SINAN cases
├── external-libs/
│   └── cbrp-simheuristic.zip              # C++ optimizer source (packaged)
├── Dockerfile                             # full image (Python+GAMA+C+++Postgres)
├── docker-entrypoint.sh                   # starts Postgres/PostGIS and runs the script
├── run-docker.sh                          # ▶ runs the SIMHEURISTIC in Docker
├── container-simulation-only/
│   ├── Dockerfile                         # simulation-only image (no C++)
│   ├── docker-entrypoint.sh
│   └── run-docker.sh                      # ▶ runs the SIMULATION ONLY in Docker
├── build-simheuristic-zip.sh              # repackages the C++ from source
└── requirements.txt
```

---

## Prerequisites

The recommended (and tested) way to run is via **Docker** — it provisions Python, GAMA headless, the C++ optimizer, and PostgreSQL/PostGIS inside the container.

- Docker installed and running.
- The file `external-libs/GAMA_1.9.2_Linux_with_JDK.zip` must be present (the `Dockerfile` unpacks it into `/external-libs/gama`).
- For the simheuristic, `external-libs/cbrp-simheuristic.zip` (the C++ optimizer source). It can be regenerated with `build-simheuristic-zip.sh` if you have the source in `~/Documentos/cbrp-methodologies`.

> **Local** execution (without Docker) is possible by installing `requirements.txt` in a venv and providing GAMA, PostgreSQL, and the C++ binary manually — but the paths in `default_connection_params["local"]` (in `src/main-simheuristic.py`) point to the author's machine and would need to be adjusted.

---

## How to run

### 1. Simheuristic (optimization + simulation)

The simplest way is the convenience script, which builds the image (if needed), starts GAMA, and runs the **batch mode** defined in `BATCH_DATES`/`BATCH_PARAMS` inside `src/main-simheuristic.py`:

```bash
./run-docker.sh
```

Useful flags:

```bash
./run-docker.sh --rebuild        # force a full image rebuild
./run-docker.sh --no-build       # never build (the image must already exist)
./run-docker.sh --no-mount       # use the code baked into the image (no src/ mount)
./run-docker.sh --rebuild-zip    # regenerate cbrp-simheuristic.zip
```

Results are written to `./docker-results/simheuristic_runs/`.

#### Running manually inside the container

`main-simheuristic.py` accepts two modes. The **batch** mode iterates over all combinations of city/dates/maps/alphas:

```bash
# inside the container (GAMA already up on port 6868)
python3 src/main-simheuristic.py batch docker /app/results-output/simheuristic_runs
```

The **single** mode runs one experiment (positional arguments):

```bash
# mode   eval    time elite iters city  map   start_date  end_date    output
python3 src/main-simheuristic.py docker default 600 5 500 AS 1000 2017-01-08 2017-01-15 /app/results-output/
```

Argument order in single mode:

| Position | Argument | Example | Meaning |
|---------:|----------|---------|---------|
| 1 | `run_mode` | `docker` / `local` | set of paths/sockets |
| 2 | `eval` | `default` / `proportional` | stochastic evaluation function |
| 3 | `max_run_time` | `600` | optimization loop time (s) |
| 4 | `elite_size` | `5` | size of the elite pool |
| 5 | `max_iters` | `500` | iterations before refreshing scenarios (surrogate) |
| 6 | `city` | `AS` / `LM` | Alto Santo / Limoeiro do Norte |
| 7 | `map_size` | `1000` | OSM map radius (m) |
| 8 | `start_date` | `2017-01-08` | start of the case window |
| 9 | `end_date` | `2017-01-15` | end of the case window |
| 10 | `output_folder` | `/app/results-output/` | output folder |

### 2. Simulation only

Use the dedicated container in `container-simulation-only/`, which **does not include the C++ optimizer** (lighter build). The script takes 3 optional parameters: output folder, previous date, and start date.

```bash
# uses the defaults (output, 2017-01-01, 2017-01-08)
./container-simulation-only/run-docker.sh

# specifying output, prev_date and start_date
./container-simulation-only/run-docker.sh /app/results-output/simulation_metrics/ 2020-07-12 2020-07-19
```

Results are written to `./docker-results/`.

#### Running manually

```bash
# build the simulation-only image
docker build -f container-simulation-only/Dockerfile -t dengue-simulation .

# run (GAMA is started by the script; here is the equivalent command)
docker run --rm -it dengue-simulation \
    bash -c 'python3 src/main.py <output_folder> <prev_date> <start_date>'
```

The `main.py` signature is:

```bash
python3 src/main.py <output_folder> <prev_date> <start_date>
#                    output folder   ref. date   simulation start date
```

---

## Main parameters

Defined in `src/main-simheuristic.py`:

- **`default_as_sim_params` / `default_lm_sim_params`** — per-city epidemiological parameters (population density, mosquitoes per person, number of breeding sites, proportion of infected mosquitoes, number of evaluation scenarios).
- **`default_connection_params`** — paths/sockets for the `local` and `docker` modes (C++ binary, GAML model, GAMA server, ZeroMQ port).
- **`BATCH_DATES`** — (start, end) windows of real cases per city in batch mode.
- **`BATCH_PARAMS`** — experiment grid: `alphas`, `map_sizes`, `max_iters_with_surrogate`, `runtime`, `elite_size`, `stochastic_evaluation`, `objective_function`.

GAML experiments available (in `dengue_propagation.gaml`):

- `dengue_propagation` — GUI experiment (`type: gui`).
- `long_headless_dengue_propagation` — batch, `repeat: 70` (base scenario / long analyses).
- `short_headless_dengue_propagation` — batch, `repeat: 20` (fast evaluation in the surrogate).

---

## Generated outputs

Per simheuristic run (in `output_folder`):

| File | Content |
|------|---------|
| `graph.txt` | Instance (nodes, arcs, cases per block) consumed by the C++ optimizer. |
| `risk_naive_analysis_boxplot.png` / `.pdf` | Boxplot: baseline × naive × elite solutions. |
| `risk_naive_analysis_stats.csv` | Statistics (min/max/avg/std, deterministic and stochastic OF) per solution. |
| `debug_report.html` | Full report: initial scenario, iterations, elite pool, solution comparison, root-cause analysis. |

Per simulation-only run:

| File | Content |
|------|---------|
| `<cfg>.csv` | Simulated cases (min/avg/max) × real per week. |
| `<cfg>_quality_metrics.csv` | Pearson correlation, MAE, count inside the endemic channel. |
| `<cfg>.pdf` | Chart of real × simulated cases over the weeks. |
| `block_infected_proportions.txt` | Proportion of blocks within the simulated range and per-block MAE. |
