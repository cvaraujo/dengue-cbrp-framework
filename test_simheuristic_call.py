#!/usr/bin/env python3
"""
Standalone stress-test for the C++ simheuristic binary (cbrp-simheur).

1. Parses a graph.txt (Limoeiro map) to extract blocks and base infected counts.
2. Generates 300 random scenarios from those base counts (Poisson-based).
3. Inserts them into PostgreSQL in 3 batches of 100 (one execution_id per batch).
4. After each load, calls `run:FULL` 500 times.
5. Produces a full report: solution diversity, OF distributions, elite tracking.

Usage:
    python3 test_simheuristic_call.py <path_to_graph.txt>
"""

import zmq
import subprocess
import threading
import time
import sys
import os
import signal
import json
import numpy as np
from collections import Counter, defaultdict
from datetime import date
from sqlalchemy import create_engine, text

# ─── Configuration ────────────────────────────────────────────────────────────
BINARY_PATH = "/home/carlos/Documentos/cbrp-methodologies/cbrp-simheur"
T = "1200"
ALPHA = 0.9
ZMQ_ADDRESS = "tcp://127.0.0.1:5556"
RUN_TIMEOUT_S = 600
INIT_WAIT_S = 10

NUM_SCENARIOS = 200
BATCH_SIZE = 100
RUNS_PER_BATCH = 300
ELITE_SIZE = 5

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "dengue-propagation"
DB_USER = "postgres"
DB_PASS = "postgres"

REPORT_DIR = "test_reports"
# ──────────────────────────────────────────────────────────────────────────────


def stream_output(pipe, label):
    t0 = time.monotonic()
    for raw in iter(pipe.readline, ""):
        elapsed = time.monotonic() - t0
        line = raw.rstrip("\n")
        if line:
            print(f"  [{label} +{elapsed:7.2f}s] {line}", flush=True)


def parse_graph(graph_path: str):
    """Parse graph.txt and return (num_blocks, {block_id: infected_count})."""
    num_blocks = 0
    infected = {}
    with open(graph_path) as f:
        header = f.readline().split()
        num_blocks = int(header[2])
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            if parts[0] == "B":
                block_id = int(parts[1])
                count = int(parts[2])
                infected[block_id] = count
    return num_blocks, infected


def generate_scenarios(num_blocks: int, base_infected: dict, num_scenarios: int, rng: np.random.Generator):
    """
    Generate random scenarios using Poisson distribution around base infected counts.
    Also adds random low-level infections in neighbouring blocks for variety.
    """
    scenarios = []
    infected_blocks = list(base_infected.keys())
    all_blocks = list(range(num_blocks))

    for _ in range(num_scenarios):
        scenario = np.zeros(num_blocks, dtype=int)

        for block, base_count in base_infected.items():
            lam = max(0.5, base_count)
            scenario[block] = rng.poisson(lam)

        num_extra = rng.integers(0, max(3, len(infected_blocks) // 3))
        extra_blocks = rng.choice(all_blocks, size=num_extra, replace=False)
        for eb in extra_blocks:
            if scenario[eb] == 0:
                scenario[eb] = rng.integers(1, 4)

        scenarios.append(scenario.tolist())

    return scenarios


def get_db_engine():
    url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(url)


def clean_test_data(engine, exec_ids):
    with engine.connect() as conn:
        for eid in exec_ids:
            conn.execute(text("DELETE FROM metrics_infected_people WHERE execution_id = :eid"), {"eid": eid})
        conn.commit()


def insert_scenarios_batch(engine, scenarios, exec_id):
    """
    Insert a batch of scenarios into metrics_infected_people.
    Each scenario becomes a simulation_id (1-based).
    Each infected person in a block becomes one row.
    """
    rows = []
    person_id = 1
    today = date.today().isoformat()

    for sim_idx, scenario in enumerate(scenarios):
        sim_id = sim_idx + 1
        for block, count in enumerate(scenario):
            for _ in range(count):
                rows.append({
                    "execution_id": exec_id,
                    "simulation_id": sim_id,
                    "cycle": 0,
                    "id": person_id,
                    "event_date": today,
                    "living_place": block,
                })
                person_id += 1

    if rows:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO metrics_infected_people
                    (execution_id, simulation_id, cycle, id, event_date, living_place)
                    VALUES (:execution_id, :simulation_id, :cycle, :id, :event_date, :living_place)
                """),
                rows,
            )
            conn.commit()

    return len(rows)


def evaluate_stochastic_of(solution_blocks: list[int], det_of: float, scenarios: list[list[int]], alpha: float):
    """Replicate the framework's default stochastic evaluation."""
    probability = 1.0 / len(scenarios)
    stochastic_of = det_of
    for block in solution_blocks:
        cases_sum = sum(probability * scenario[block] for scenario in scenarios)
        stochastic_of += alpha * cases_sum
    return stochastic_of


class EliteTracker:
    """Tracks the elite set and counts updates."""

    def __init__(self, max_size: int):
        self.max_size = max_size
        self.solutions = []
        self.update_count = 0
        self.update_log = []

    def try_insert(self, blocks_key: str, det_of: float, stoch_of: float, iteration: int, phase: str):
        """Try to insert a solution. Returns True if elite was updated."""
        entry = (stoch_of, det_of, blocks_key)

        if len(self.solutions) < self.max_size:
            self.solutions.append(entry)
            self.solutions.sort(reverse=True)
            self.update_count += 1
            self.update_log.append({"iter": iteration, "phase": phase, "stoch_of": stoch_of, "det_of": det_of})
            return True

        worst = self.solutions[-1]
        if stoch_of > worst[0]:
            self.solutions[-1] = entry
            self.solutions.sort(reverse=True)
            self.update_count += 1
            self.update_log.append({"iter": iteration, "phase": phase, "stoch_of": stoch_of, "det_of": det_of})
            return True

        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_simheuristic_call.py <path_to_graph.txt>")
        sys.exit(1)

    graph_path = os.path.abspath(sys.argv[1])
    if not os.path.isfile(graph_path):
        print(f"ERROR: graph file not found at {graph_path}")
        sys.exit(1)
    if not os.path.isfile(BINARY_PATH):
        print(f"ERROR: binary not found at {BINARY_PATH}")
        sys.exit(1)

    # ─── Parse graph ──────────────────────────────────────────────────────────
    print(f"[1] Parsing graph: {graph_path}")
    num_blocks, base_infected = parse_graph(graph_path)
    total_base_cases = sum(base_infected.values())
    print(f"    Blocks: {num_blocks}")
    print(f"    Infected blocks: {len(base_infected)} (total cases: {total_base_cases})")

    # ─── Generate scenarios ───────────────────────────────────────────────────
    print(f"\n[2] Generating {NUM_SCENARIOS} random scenarios ...")
    rng = np.random.default_rng(seed=42)
    all_scenarios = generate_scenarios(num_blocks, base_infected, NUM_SCENARIOS, rng)

    scenario_totals = [sum(s) for s in all_scenarios]
    print(f"    Cases per scenario — min: {min(scenario_totals)}, "
          f"max: {max(scenario_totals)}, mean: {np.mean(scenario_totals):.1f}, "
          f"std: {np.std(scenario_totals):.1f}")

    # ─── Prepare batches ─────────────────────────────────────────────────────
    num_batches = (NUM_SCENARIOS + BATCH_SIZE - 1) // BATCH_SIZE
    batches = [all_scenarios[i * BATCH_SIZE:(i + 1) * BATCH_SIZE] for i in range(num_batches)]
    exec_ids = [9000 + i for i in range(num_batches)]
    print(f"    Batches: {num_batches} x {BATCH_SIZE} scenarios (exec_ids: {exec_ids})")

    # ─── Clean old test data from DB ──────────────────────────────────────────
    print(f"\n[3] Connecting to PostgreSQL and cleaning test data ...")
    engine = get_db_engine()
    clean_test_data(engine, exec_ids)
    print("    Done.")

    # ─── Start C++ binary ─────────────────────────────────────────────────────
    print(f"\n[4] Starting cbrp-simheur ...")
    print(f"    {BINARY_PATH} {graph_path} {T} {ALPHA} {ZMQ_ADDRESS}")
    proc = subprocess.Popen(
        [BINARY_PATH, graph_path, T, str(ALPHA), ZMQ_ADDRESS],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    reader = threading.Thread(target=stream_output, args=(proc.stdout, "C++"), daemon=True)
    reader.start()
    print(f"    PID = {proc.pid}")
    print(f"    Waiting {INIT_WAIT_S}s for init (graph loading + Floyd-Warshall) ...")
    time.sleep(INIT_WAIT_S)

    if proc.poll() is not None:
        print(f"ERROR: binary exited early with code {proc.returncode}")
        sys.exit(1)

    # ─── Connect ZMQ ──────────────────────────────────────────────────────────
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REQ)
    sock.setsockopt(zmq.LINGER, 0)
    sock.connect(ZMQ_ADDRESS)

    def zmq_call(msg: str, timeout_s: int = 60) -> str | None:
        sock.setsockopt(zmq.RCVTIMEO, timeout_s * 1000)
        t0 = time.monotonic()
        sock.send_string(msg)
        try:
            reply = sock.recv_string()
            return reply
        except zmq.Again:
            elapsed = time.monotonic() - t0
            print(f"  !!! TIMEOUT after {elapsed:.2f}s on '{msg}'")
            return None

    def reset_socket():
        nonlocal sock
        sock.close()
        sock = ctx.socket(zmq.REQ)
        sock.setsockopt(zmq.LINGER, 0)
        sock.connect(ZMQ_ADDRESS)

    # ─── Check connection ─────────────────────────────────────────────────────
    print("\n[5] Checking connection ...")
    reply = zmq_call("check_conn", timeout_s=10)
    if reply != "connected":
        print(f"ERROR: expected 'connected', got '{reply}'")
        proc.kill()
        sys.exit(1)
    print("    Connected!")

    # ─── Main experiment loop ─────────────────────────────────────────────────
    elite = EliteTracker(ELITE_SIZE)
    phase_results = []
    cumulative_scenarios = []
    global_iteration = 0

    for batch_idx, (batch, exec_id) in enumerate(zip(batches, exec_ids)):
        phase_name = f"batch_{batch_idx + 1}"
        cumulative_scenarios.extend(batch)
        num_loaded = len(cumulative_scenarios)

        print(f"\n{'=' * 70}")
        print(f"  PHASE {batch_idx + 1}/{num_batches}: loading {len(batch)} scenarios "
              f"(exec_id={exec_id}, cumulative={num_loaded})")
        print(f"{'=' * 70}")

        # Insert into DB
        print(f"  Inserting scenarios into PostgreSQL ...")
        t0 = time.monotonic()
        num_rows = insert_scenarios_batch(engine, batch, exec_id)
        print(f"    Inserted {num_rows} rows in {time.monotonic() - t0:.2f}s")

        # Load into C++
        print(f"  Sending load:{exec_id} ...")
        t0 = time.monotonic()
        reply = zmq_call(f"load:{exec_id}", timeout_s=60)
        print(f"    Reply: '{reply}' ({time.monotonic() - t0:.2f}s)")
        if reply != "loaded":
            print(f"  WARNING: unexpected load reply: {reply}")

        # Run optimisation N times
        print(f"  Running {RUNS_PER_BATCH} optimisation calls ...")
        solutions = []
        run_times = []
        errors = 0

        for i in range(RUNS_PER_BATCH):
            t0 = time.monotonic()
            reply = zmq_call("run:FULL", timeout_s=RUN_TIMEOUT_S)
            elapsed = time.monotonic() - t0
            run_times.append(elapsed)

            if reply is None:
                errors += 1
                print(f"    [{i + 1}/{RUNS_PER_BATCH}] TIMEOUT — resetting socket")
                reset_socket()
                reply_check = zmq_call("check_conn", timeout_s=10)
                if reply_check != "connected":
                    print(f"    FATAL: lost connection after timeout, aborting phase")
                    break
                continue

            parts = reply.split(":")
            if parts[0] == "solution":
                blocks_str = parts[1]
                det_of = float(parts[2])
                blocks_list = [int(b) for b in blocks_str.split(",")]
                stoch_of = evaluate_stochastic_of(blocks_list, det_of, cumulative_scenarios, ALPHA)
                blocks_key = ",".join(str(b) for b in sorted(blocks_list))

                solutions.append({
                    "blocks": blocks_list,
                    "blocks_key": blocks_key,
                    "det_of": det_of,
                    "stoch_of": stoch_of,
                    "time_s": elapsed,
                })

                elite.try_insert(blocks_key, det_of, stoch_of, global_iteration, phase_name)
            else:
                errors += 1
                print(f"    [{i + 1}/{RUNS_PER_BATCH}] unexpected: {reply}")

            global_iteration += 1

            if (i + 1) % 100 == 0:
                distinct = len(set(s["blocks_key"] for s in solutions))
                avg_det = np.mean([s["det_of"] for s in solutions]) if solutions else 0
                avg_stoch = np.mean([s["stoch_of"] for s in solutions]) if solutions else 0
                print(f"    [{i + 1}/{RUNS_PER_BATCH}] solutions={len(solutions)}, "
                      f"distinct={distinct}, avg_det_of={avg_det:.2f}, avg_stoch_of={avg_stoch:.2f}, "
                      f"elite_updates={elite.update_count}, errors={errors}")

        # Phase summary
        if solutions:
            det_ofs = [s["det_of"] for s in solutions]
            stoch_ofs = [s["stoch_of"] for s in solutions]
            distinct_keys = set(s["blocks_key"] for s in solutions)
            block_counts = [len(s["blocks"]) for s in solutions]

            phase_summary = {
                "phase": phase_name,
                "cumulative_scenarios": num_loaded,
                "num_runs": len(solutions),
                "errors": errors,
                "distinct_solutions": len(distinct_keys),
                "det_of_min": float(np.min(det_ofs)),
                "det_of_max": float(np.max(det_ofs)),
                "det_of_mean": float(np.mean(det_ofs)),
                "det_of_std": float(np.std(det_ofs)),
                "stoch_of_min": float(np.min(stoch_ofs)),
                "stoch_of_max": float(np.max(stoch_ofs)),
                "stoch_of_mean": float(np.mean(stoch_ofs)),
                "stoch_of_std": float(np.std(stoch_ofs)),
                "blocks_min": int(np.min(block_counts)),
                "blocks_max": int(np.max(block_counts)),
                "blocks_mean": float(np.mean(block_counts)),
                "avg_time_s": float(np.mean(run_times)),
                "elite_updates_total": elite.update_count,
            }
            phase_results.append(phase_summary)

            freq = Counter(s["blocks_key"] for s in solutions)
            top5 = freq.most_common(5)

            print(f"\n  ─── Phase {batch_idx + 1} Summary ───")
            print(f"  Solutions: {len(solutions)} ({len(distinct_keys)} distinct)")
            print(f"  Det. OF  — min: {np.min(det_ofs):.2f}, max: {np.max(det_ofs):.2f}, "
                  f"mean: {np.mean(det_ofs):.2f}, std: {np.std(det_ofs):.2f}")
            print(f"  Stoch.OF — min: {np.min(stoch_ofs):.2f}, max: {np.max(stoch_ofs):.2f}, "
                  f"mean: {np.mean(stoch_ofs):.2f}, std: {np.std(stoch_ofs):.2f}")
            print(f"  Blocks   — min: {np.min(block_counts)}, max: {np.max(block_counts)}, "
                  f"mean: {np.mean(block_counts):.1f}")
            print(f"  Avg time per run: {np.mean(run_times):.3f}s")
            print(f"  Elite updates so far: {elite.update_count}")
            print(f"  Top-5 most frequent solutions:")
            for rank, (key, cnt) in enumerate(top5, 1):
                matching = [s for s in solutions if s["blocks_key"] == key]
                det = matching[0]["det_of"]
                stoch = matching[0]["stoch_of"]
                print(f"    #{rank}: freq={cnt}/{len(solutions)} "
                      f"({cnt / len(solutions) * 100:.1f}%) "
                      f"det_of={det:.2f} stoch_of={stoch:.2f} "
                      f"blocks=[{key[:80]}{'...' if len(key) > 80 else ''}]")

    # ─── Stop C++ binary ──────────────────────────────────────────────────────
    print(f"\n[6] Sending stop ...")
    try:
        sock.setsockopt(zmq.RCVTIMEO, 5000)
        sock.send_string("stop")
        sock.recv_string()
    except Exception:
        pass

    sock.close()
    ctx.term()

    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    print(f"    Binary exited with code {proc.returncode}")

    # ─── Clean DB ─────────────────────────────────────────────────────────────
    print(f"\n[7] Cleaning test data from PostgreSQL ...")
    clean_test_data(engine, exec_ids)
    engine.dispose()
    print("    Done.")

    # ─── Final Report ─────────────────────────────────────────────────────────
    os.makedirs(REPORT_DIR, exist_ok=True)

    print(f"\n{'=' * 70}")
    print(f"  FINAL REPORT")
    print(f"{'=' * 70}")
    print(f"  Graph: {graph_path}")
    print(f"  Blocks: {num_blocks}, Infected blocks: {len(base_infected)}, "
          f"Base cases: {total_base_cases}")
    print(f"  Scenarios generated: {NUM_SCENARIOS}")
    print(f"  Batches: {num_batches} x {BATCH_SIZE}")
    print(f"  Runs per batch: {RUNS_PER_BATCH}")
    print(f"  Alpha: {ALPHA}")
    print()

    print("  ─── Per-Phase Results ───")
    print(f"  {'Phase':<10} {'Scen':>5} {'Runs':>5} {'Distinct':>8} "
          f"{'DetOF_mean':>10} {'DetOF_std':>9} {'StochOF_mean':>12} {'StochOF_std':>11} "
          f"{'EliteUpd':>8}")
    print(f"  {'-' * 89}")
    for pr in phase_results:
        print(f"  {pr['phase']:<10} {pr['cumulative_scenarios']:>5} {pr['num_runs']:>5} "
              f"{pr['distinct_solutions']:>8} "
              f"{pr['det_of_mean']:>10.2f} {pr['det_of_std']:>9.2f} "
              f"{pr['stoch_of_mean']:>12.2f} {pr['stoch_of_std']:>11.2f} "
              f"{pr['elite_updates_total']:>8}")

    print(f"\n  ─── Elite Set (Top {ELITE_SIZE}) ───")
    for rank, (stoch_of, det_of, blocks_key) in enumerate(elite.solutions, 1):
        nblocks = len(blocks_key.split(","))
        print(f"    #{rank}: stoch_of={stoch_of:.4f}  det_of={det_of:.2f}  "
              f"num_blocks={nblocks}  blocks=[{blocks_key[:60]}{'...' if len(blocks_key) > 60 else ''}]")

    print(f"\n  ─── Elite Update History ({elite.update_count} total updates) ───")
    for entry in elite.update_log:
        print(f"    iter={entry['iter']:>5}  phase={entry['phase']:<10} "
              f"stoch_of={entry['stoch_of']:.4f}  det_of={entry['det_of']:.2f}")

    print(f"\n  ─── Variability Analysis ───")
    if len(phase_results) > 1:
        first = phase_results[0]
        last = phase_results[-1]
        print(f"    Distinct solutions: {first['distinct_solutions']} (batch 1) → "
              f"{last['distinct_solutions']} (batch {len(phase_results)})")
        print(f"    Det. OF std:        {first['det_of_std']:.2f} → {last['det_of_std']:.2f}")
        print(f"    Stoch. OF std:      {first['stoch_of_std']:.2f} → {last['stoch_of_std']:.2f}")

        if first['distinct_solutions'] > 0:
            diversity_change = (last['distinct_solutions'] - first['distinct_solutions']) / first['distinct_solutions'] * 100
            print(f"    Diversity change:   {diversity_change:+.1f}%")

    # Save JSON report
    report = {
        "config": {
            "graph": graph_path,
            "num_blocks": num_blocks,
            "base_infected_blocks": len(base_infected),
            "base_total_cases": total_base_cases,
            "num_scenarios": NUM_SCENARIOS,
            "batch_size": BATCH_SIZE,
            "runs_per_batch": RUNS_PER_BATCH,
            "alpha": ALPHA,
            "elite_size": ELITE_SIZE,
            "T": T,
        },
        "phases": phase_results,
        "elite_set": [
            {"rank": i + 1, "stoch_of": s[0], "det_of": s[1], "blocks": s[2]}
            for i, s in enumerate(elite.solutions)
        ],
        "elite_updates": elite.update_log,
    }
    report_path = os.path.join(REPORT_DIR, "simheuristic_test_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report saved to: {report_path}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
