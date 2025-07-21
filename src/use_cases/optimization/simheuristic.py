import os, zmq, subprocess, time, heapq, threading
import numpy as np
from typing import List
from datetime import datetime
from venv import logger
import adapters.json.json_adapter as JsonAdapter
from domain.osm import OpenStreetMap
from domain.graph import Graph
from adapters.osm.map_adapter import MapAdapter
from adapters.sql.postgree import PostgreSQLAdapter
from use_cases.simulation import Simulation
from use_cases.scenario_generation import ScenarioGeneration
import domain.utils as Utils
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

class Solution:
    def __init__(self, blocks: list[int], deterministic_of: float, stochastic_of: float):
        self._blocks = blocks
        self._deterministic_of = deterministic_of
        self._stochastic_of = stochastic_of

    def __str__(self):
        return f"Solution(blocks={self._blocks}, deterministic_of={self._deterministic_of}, stochastic_of={self._stochastic_of})"
    
    def get_blocks(self) -> list[int]:
        return self._blocks
    
    def get_deterministic_of(self) -> float:
        return self._deterministic_of
    
    def set_stochastic_of(self, stochastic_of: float):
        self._stochastic_of = stochastic_of

    def get_stochastic_of(self) -> float:
        return self._stochastic_of
    
    def __lt__(self, other):
        return self._deterministic_of > other.get_deterministic_of()


class SimheuristicFramework:
    def __init__(
        self,
        output_folder: str,
        run_params: dict,
        simulation_params: dict,
        optimization_params: dict,
        simulation: Simulation,
        stochastic_evaluation: str = "default",
    ):
        self._output_folder = output_folder
        self._sim_params = simulation_params
        self._opt_params = optimization_params
        self._run_params = run_params
        self._exec_id = 0
        self._simulation = simulation
        self._db = PostgreSQLAdapter()
        self._scenarios: List[List[int]] = []
        self._best_deterministic_solution = None
        self._elite_stochastic_solutions = []
        self._run_id = 0
        self._use_surrogate_model = True
        self._alpha = 0.8
        self._stochastic_evaluation = stochastic_evaluation

    def _get_sim_param(self, param_key: str):
        try:
            param = self._sim_params[param_key]
            return param
        except KeyError:
            logger.warning(f"[!] Simulation parameter {param_key} not found!")

    def _get_opt_param(self, param_key: str):
        try:
            param = self._opt_params[param_key]
            return param
        except KeyError:
            logger.warning(f"[!] Optimization parameter {param_key} not found!")

    def _get_run_param(self, param_key: str):
        try:
            param = self._run_params[param_key]
            return param
        except KeyError:
            logger.warning(f"[!] Run parameter {param_key} not found!")

    def _start_optimization_executable(self):
        try:
            project_dir: str = self._get_opt_param("project_dir")
            subprocess.run(["cmake", project_dir], check=True, cwd=project_dir)
            subprocess.run(["make", "-C", project_dir, "cbrp-simheur", "-j"], check=True, cwd=project_dir)
            
            binary_path: str = self._get_opt_param("executable_path")
            socket_str: str = self._get_opt_param("socket_str")
            max_time_route: str = self._get_opt_param("max_time_route")
            input_graph: str = os.path.abspath(os.path.join(self._output_folder, "graph.txt"))

            process = subprocess.Popen(
                [binary_path, input_graph, max_time_route, socket_str],
                stdout=subprocess.PIPE,
                text=True,
            )
            
            # Start async output monitoring
            def monitor_output(pipe, prefix):
                for line in iter(pipe.readline, ''):
                    if line:
                        logger.info(f"{prefix}: {line.strip()}")
            
            stdout_thread = threading.Thread(target=monitor_output, args=(process.stdout, "STDOUT"))
            stdout_thread.daemon = True
            stdout_thread.start()
        except Exception as e:
            logger.error(f"[!] Error starting optimization executable: {e}")
            exit(1)
        
    def _call_optimization(self, action: str = "run") -> Solution | None:
        message = action
        if action == "load":
            message += f":{self._run_id}"

        logger.info(f"[*] Preparing to send message to optimization: {message}")

        for attempt in range(1, self._socket_max_retries + 1):
            try:
                logger.info(f"[*] Attempt {attempt}: sending message '{message}'")
                self._socket.send_string(message)

                logger.info("[*] Waiting for response...")
                reply = self._socket.recv_string()

                logger.info(f"[*] Received response from optimization: {reply}")
                response: list[str] = reply.split(":")
                solution = None

                if response[0] == "solution":
                    sol_blocks: list[int] = [int(b) for b in response[1].split(",")]
                    sol_det_of: float = float(response[2])
                    solution = Solution(sol_blocks, sol_det_of, 0.0)

                return solution

            except zmq.Again:
                logger.warning(f"[!] Timeout waiting for response (attempt {attempt})")
                time.sleep(self._socket_retry_interval)
            except zmq.ZMQError as e:
                logger.error(f"[!] ZMQ Error: {e}")

        logger.error("[!] Failed to receive response from optimization after multiple attempts.")
        return None

    def _check_optimization_status(self):
        try:
            self._socket.send_string("check_conn")
            while True:
                reply = self._socket.recv_string()
                if reply == "connected":
                    logger.info("[*] Optimization executable connected successfully")
                    return True
                else:
                    logger.warning(f"[!] Unexpected message while waiting for 'connected': {reply}")
                    time.sleep(1)
        except zmq.ZMQError as e:
            logger.error(f"[!] ZMQ Error while waiting for 'connected': {e}")
            return
        except Exception as e:
            logger.error(f"[!] Error checking optimization status: {e}")
            return

    def _compute_start_scenarios(self):
        self._run_id += 1
        self._call_simulation(max_cycles=14, is_batch=True, is_short=False)
        scenarios: List[List[int]] = self._get_scenario_cases_per_block()
        self._scenarios.extend(scenarios)
        self._use_surrogate_model = True

    def _evaluate_deterministic_solution(self, solution: Solution) -> float:
        selected_scenarios: List[List[int]] = []
        if (self._use_surrogate_model):
            num_scenarios_evaluation = self._get_sim_param("num_scenarios_evaluation")
            random_scenarios = np.random.choice(len(self._scenarios), num_scenarios_evaluation, replace=False)
            selected_scenarios = [self._scenarios[i] for i in random_scenarios]
        else:
            self._run_id += 1
            self._call_simulation(max_cycles=14, is_batch=True, is_short=True)
            selected_scenarios: List[List[int]] = self._get_scenario_cases_per_block()
            self._scenarios.extend(selected_scenarios)
            self._call_optimization(action="load")
            self._use_surrogate_model = True
        
        stochastic_of = 0.0
        if self._stochastic_evaluation == "default":
            stochastic_of = self._get_default_stochastic_value(solution, selected_scenarios)
        elif self._stochastic_evaluation == "proportional":
            stochastic_of = self._get_proportional_stochastic_value(solution, selected_scenarios)

        solution.set_stochastic_of(stochastic_of)
        return stochastic_of

    def _get_default_stochastic_value(self, solution: Solution, scenarios: List[List[int]]):
        stochastic_of: float = solution.get_deterministic_of();
        probability: float = 1.0 / float(len(scenarios))

        for block in solution.get_blocks():
            all_scenarios_cases: float = 0.0
            for scenario in scenarios:
                all_scenarios_cases += probability * scenario[block]
            stochastic_of += self._alpha * all_scenarios_cases

        return stochastic_of
    
    def _get_proportional_stochastic_value(self, solution: Solution, scenarios: List[List[int]]):
        stochastic_of: float = solution.get_deterministic_of();
        solution_blocks = solution.get_blocks()

        for scenario in scenarios:
            total_cases: float = 0
            evited_cases: float = 0

            for block, cases in enumerate(scenario):
                total_cases += cases

                if block in solution_blocks:
                    evited_cases += cases

            if evited_cases > 0:
                stochastic_of += ((evited_cases * self._alpha)/total_cases)

        return stochastic_of

    def _call_simulation(self, max_cycles: int, is_batch: bool = False, is_short: bool = True, nebulize_solution: int = -1):
        logger.info("[*] Running Simulation...")
        start_date = self._get_run_param("start_date")

        params = Utils.prepare_parameters(
            self._shp_path,
            self._exec_id,
            self._run_id,
            start_date,
            max_cycles=max_cycles,
            save_states=is_batch,
            nebulize_solution=nebulize_solution
        )

        header = JsonAdapter.convert_param_2_list(params)
        self._simulation.run_simulation(header, is_batch=is_batch, is_short=is_short)

    def _get_scenario_cases_per_block(self) -> List[List[int]]:
        logger.info("[*] Extracting and aggregating simulated cases...")
        sim_cases = self._db.query(
            f"SELECT * FROM metrics_infected_people WHERE execution_id = {self._run_id}"
        ).drop_duplicates(subset=["id"])

        grouped = sim_cases.groupby(
            ["living_place", "simulation_id"], as_index=False
        ).count()

        b = self._graph.b
        num_scenarios = np.max(grouped["simulation_id"].unique())

        all_scenarios = [
            grouped[grouped["simulation_id"] == s]
            .set_index("living_place")["id"]
            .reindex(range(b), fill_value=0)
            .tolist()
            for s in range(1, num_scenarios + 1)
        ]

        return all_scenarios

    def _compute_metrics(self):
        pass

    def _write_graph(self, filename: str):
        logger.info("[*] Writing graph...")
        with open(filename, "w") as file:
            file.write(f"{self._graph.n} {self._graph.m} {self._graph.b}\n")
            for id, node in self._graph.nodes.items():
                blocks = ",".join(str(b) for b in node.get_blocks())
                file.write(f"N {id} {node.lat:.6f} {node.lon:.6f} {blocks}\n")

            for idx in range(self._graph.n):
                for arc in self._graph.arcs[idx]:
                    block = -1 if arc.block == -1 else arc.block
                    file.write(
                        f"A {arc.source.index} {arc.target.index} {arc.length:.3f} {block}\n"
                    )

            for i, infected in enumerate(self._infected_per_block):
                if infected > 0:
                    file.write(f"B {i} {infected}\n")

    def _create_base_environment(self):
        logger.info("[*] Clearing old data...")
        self._db.clear_database()

        # Inital parameters
        city_key = self._get_run_param("city")
        city, _ = Utils.get_city_info(city_key)
        map_size = self._get_run_param("map_size")
        start_date = self._get_run_param("start_date")
        end_date = self._get_run_param("end_date")

        logger.info(f"[*] Loading OSM map: {city} ({map_size})...")
        osm = OpenStreetMap(city, map_size)
        self._graph: Graph = MapAdapter.convert_osm_to_graph(osm, True)

        logger.info("[*] Retrieving dengue cases...")
        cases = self._db.get_notifications_between_dates(start_date, end_date, city)
        logger.info("[*] Processing blocks and population data...")
        people_per_km2 = self._get_sim_param("people_per_km2")
        
        coord_blocks = Utils.all_blocks_as_polygons(self._graph)
        people_block = Utils.compute_people_per_block(self._graph, people_per_km2, coord_blocks)
        
        self._infected_per_block, recovered = (
            Utils.get_infected_recovered_people_per_block(
                cases,
                self._graph,
                datetime.strptime(start_date, "%Y-%m-%d"),
                coord_blocks,
            )
        )
        self._write_graph(os.path.join(self._output_folder, "graph.txt"))

        logger.info("[*] Creating starting scenario into Database...")
        self._scenario_generator = ScenarioGeneration(
            execution_id=self._exec_id,
            simulation_id=0,
            cycle=0,
            started_from_cycle=0,
            start_date=start_date,
            connection=self._db,
        )

        # Simulation Parameters
        mosquitoes_per_person = self._get_sim_param("mosquitoes_per_person")
        nb_breeding_sites = self._get_sim_param("nb_breeding_sites")
        proportion_infected_mosquitoes_without_cases = self._get_sim_param(
            "proportion_infected_mosquitoes_without_cases"
        )
        proportion_infected_mosquitoes_with_cases = self._get_sim_param(
            "proportion_infected_mosquitoes_with_cases"
        )

        self._scenario_generator.create_starting_scenario(
            people_per_block=people_block,
            infected_people_per_block=self._infected_per_block,
            recovered_people_per_block=recovered,
            mosquitoes_per_person=mosquitoes_per_person,
            nb_breeding_sites=nb_breeding_sites,
            proportion_infected_mosquitoes_without_cases=proportion_infected_mosquitoes_without_cases,
            proportion_infected_mosquitoes_with_cases=proportion_infected_mosquitoes_with_cases,
        )

        logger.info("[*] Exporting SHP files...")
        self._shp_path = Utils.build_shapefile_path(city, map_size)
        MapAdapter.export_osm_to_shapefile(osm, self._graph, self._shp_path)

        # Set starting scenario in GAMA
        self._call_simulation(max_cycles=0, is_batch=False)

    def clear_run(self):
        self._db.clear_database()
        # self._simulation.kill_gama_headless()

    def risk_analysis(self):
        boxplot_data, stats_data = [], []        

        # Base scenario
        self._run_id += 1
        self._call_simulation(max_cycles=14, is_batch=True, is_short=False)
        scenarios: List[List[int]] = self._get_scenario_cases_per_block()
        scenario_sums = [sum(s) for s in scenarios]

        for cs in scenario_sums:
            boxplot_data.append({
                "stochastic_of": "baseline", 
                "value": cs,
                "type": "Original"
            })

        stats_data.append({
            "id": "Original",
            "min": np.min(scenario_sums),
            "max": np.max(scenario_sums),
            "avg": np.mean(scenario_sums),
            "deterministic_of": 0,
            "stochastic_of": 0.0
        })

        for solution in self._elite_stochastic_solutions:
            self._run_id += 1
            self._db.run_query_insert_solution(self._run_id, solution.get_blocks())
            self._call_simulation(max_cycles=14, is_batch=True, is_short=False, nebulize_solution=self._run_id)

            nebulized_scenarios: List[List[int]] = self._get_scenario_cases_per_block()
            nebulized_scenario_sums = [sum(s) for s in nebulized_scenarios]

            if self._stochastic_evaluation == "default":
                stochastic_of = self._get_default_stochastic_value(solution, scenarios)
            elif self._stochastic_evaluation == "proportional":
                stochastic_of = self._get_proportional_stochastic_value(solution, scenarios)

            solution.set_stochastic_of(stochastic_of)

            logger.info(f"Det. OF: {solution.get_deterministic_of()}, Stochastic OF: {round(stochastic_of, 4)}")

            for nebu in nebulized_scenario_sums:
                boxplot_data.append({
                    "stochastic_of": f"OF = {round(stochastic_of, 4)}",
                    "value": nebu,
                    "type": "Nebulized"
                })

            stats_data.append({
                "id": "Nebulized",
                "min": np.min(nebulized_scenario_sums),
                "max": np.max(nebulized_scenario_sums),
                "avg": np.mean(nebulized_scenario_sums),
                "deterministic_of": solution.get_deterministic_of(),
                "stochastic_of": stochastic_of
            })

        df = pd.DataFrame(boxplot_data)
        num_solutions = max(1, len(self._elite_stochastic_solutions))
        width = max(12, 4 * num_solutions)
        plt.figure(figsize=(width, 9))
        sns.boxplot(
            x="stochastic_of",
            y="value",
            hue="type",
            data=df,
            palette={"Original": "skyblue", "Nebulized": "salmon"},
            dodge=True,
            gap=0.1,
            width=0.2
        )
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_csv(os.path.join(self._output_folder, "risk_analysis_stats.csv"), index=False)

        plt.xlabel("Stochastic Objective Function Value")
        plt.ylabel("Scenario Total Cases")
        plt.title("Risk Analysis: Distribution of Scenario Sums by Stochastic OF")
        plt.xticks()
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.legend(title="Scenario Type")
        plt.tight_layout()
        plt.savefig(os.path.join(self._output_folder, "risk_analysis_boxplot.png"))
        plt.close()

    def run(self, socket_str: str, max_time_seconds: int = 120, elite_size: int = 10, max_iters_with_surrogate: int = 100):
        self._create_base_environment()
        self._start_optimization_executable()

        # Socket configuration
        self._socket_str = socket_str
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REQ)
        self._socket.connect(self._socket_str)
        self._socket_max_retries = 5
        self._socket_retry_interval = 1
        self._socket.setsockopt(zmq.RCVTIMEO, 1000)
        self._socket.setsockopt(zmq.LINGER, 0)

        logger.info("[*] Computing first solution...")
        if self._check_optimization_status():            
            logger.info("[*] Generating start scenarios (Long Simulation of 14 cycles)...")
            self._compute_start_scenarios()
            start_solution = self._call_optimization(action="load")
            start_solution = self._call_optimization(action="run")
        else:
            logger.error("[!] Optimization executable not connected after multiple attempts.")
            return

        if (start_solution is None):
            logger.error("[!] Failed to receive response from optimization after multiple attempts.")
            return

        logger.info("[*] Evaluating first solution...")
        self._evaluate_deterministic_solution(start_solution)
        self._best_deterministic_solution = start_solution
        heapq.heappush(self._elite_stochastic_solutions, start_solution)

        logger.info("[*] Starting the First Stage...")
        start_time = time.time()
        elapsed_time: float = 0.0
        iterations = 0
        
        while elapsed_time < max_time_seconds:
            opt_start_time = time.time()
            new_det_solution = self._call_optimization(action="run")
            
            if (new_det_solution is None):
                logger.error("[!] Failed to receive response from optimization after multiple attempts.")
                return

            logger.info(f"Optimization time: {time.time() - opt_start_time:.2f} seconds")

            eval_start_time = time.time()
            stochastic_of = self._evaluate_deterministic_solution(new_det_solution)
            logger.info(f"Evaluation time: {time.time() - eval_start_time:.2f} seconds")
    
            if (stochastic_of > self._best_deterministic_solution.get_stochastic_of()):
                self._best_deterministic_solution = new_det_solution
                heapq.heappush(self._elite_stochastic_solutions, new_det_solution)  

                if (len(self._elite_stochastic_solutions) > elite_size):
                    heapq.heappop(self._elite_stochastic_solutions)

            iterations += 1
            if (iterations >= max_iters_with_surrogate):
                self._use_surrogate_model = False
                iterations = 0
            
            elapsed_time = time.time() - start_time
            logger.info(f"Elapsed time in iteration {iterations}: {elapsed_time:.2f} seconds")
        
        self._call_optimization(action="stop")
        
        risk_start_time = time.time()
        self.risk_analysis()
        logger.info(f"Risk analysis time: {time.time() - risk_start_time:.2f} seconds")

        # Clean up
        self._socket.close()    
        self._context.term()
            