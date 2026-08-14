import os, zmq, subprocess, time, heapq, threading
import numpy as np
from typing import List
from datetime import datetime, timedelta
import logging
logger = logging.getLogger(__name__)
from shapely import Polygon, Point
import adapters.json.json_adapter as JsonAdapter
from domain.osm import OpenStreetMap
from domain.graph import Graph
from adapters.osm.map_adapter import MapAdapter
from adapters.sql.postgree import PostgreSQLAdapter
from use_cases.simulation import Simulation
from use_cases.scenario_generation import ScenarioGeneration
import domain.utils as Utils
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import seaborn as sns
import pandas as pd

def get_city_info(city: str):
    if city == "Alto Santo, Ceará, Brasil":
        return "ALTO SANTO", "alto-santo"
    if city == "Guaratiba, Rio de Janeiro, Brasil":
        return "GT", "guaratiba"
    if city == "Limoeiro do Norte, Ceará, Brasil":
        return "LIMOEIRO", "limoeiro"
    raise ValueError(f"City '{city}' is not supported")

class Solution:
    def __init__(self, blocks: list[int], deterministic_of: float, stochastic_of: float):
        self._blocks = blocks
        self._deterministic_of = deterministic_of
        self._stochastic_of = stochastic_of

    def __str__(self):
        return f"Solution(blocks={self._blocks}, deterministic_of={self._deterministic_of}, stochastic_of={self._stochastic_of})"
    
    def get_blocks(self) -> list[int]:
        return self._blocks
    
    def set_deterministic_of(self, deterministic_of: float):
        self._deterministic_of = deterministic_of

    def get_deterministic_of(self) -> float:
        return self._deterministic_of
    
    def set_stochastic_of(self, stochastic_of: float):
        self._stochastic_of = stochastic_of

    def get_stochastic_of(self) -> float:
        return self._stochastic_of
    
    def __lt__(self, other):
        if self._deterministic_of == other.get_deterministic_of():
            return self._stochastic_of > other.get_stochastic_of()
        return self._deterministic_of > other.get_deterministic_of()


class SimheuristicFramework:
    def __init__(
        self,
        output_folder: str,
        run_params: dict,
        simulation_params: dict,
        optimization_params: dict,
        simulation: Simulation,
        alpha_model: float = 0.8,
        stochastic_evaluation: str = "default",
        objective_function: str = "RANDOM",
    ):
        self._graph: Graph = None
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
        self._alpha = alpha_model
        self._stochastic_evaluation = stochastic_evaluation
        self._objective_function = objective_function
        self._debug_data = {
            "config": {},
            "initial_scenario": {},
            "optimization_iterations": [],
            "elite_solutions": [],
            "risk_analysis": {},
        }

    def _collect_initial_scenario_debug(self):
        logger.info("[DEBUG] Collecting initial scenario data...")
        d = self._debug_data["initial_scenario"]

        d["infected_per_block"] = self._infected_per_block.tolist() if hasattr(self._infected_per_block, 'tolist') else list(self._infected_per_block)
        d["total_blocks"] = self._graph.b
        d["total_initial_infected_people"] = int(np.sum(self._infected_per_block))

        mosquitoes_df = self._db.query(
            "SELECT curr_building, state, COUNT(*) as cnt FROM mosquitoes "
            "WHERE execution_id=0 AND simulation_id=0 AND cycle=0 "
            "GROUP BY curr_building, state"
        )
        people_df = self._db.query(
            "SELECT living_place, state, COUNT(*) as cnt FROM people "
            "WHERE execution_id=0 AND simulation_id=0 AND cycle=0 "
            "GROUP BY living_place, state"
        )
        bs_df = self._db.query(
            "SELECT curr_building, COUNT(*) as cnt FROM breeding_sites "
            "WHERE execution_id=0 AND simulation_id=0 AND cycle=0 "
            "GROUP BY curr_building"
        )
        eggs_df = self._db.query(
            "SELECT COUNT(*) as cnt FROM eggs "
            "WHERE execution_id=0 AND simulation_id=0 AND cycle=0"
        )

        mosq_per_block = {}
        for _, row in mosquitoes_df.iterrows():
            blk = int(row["curr_building"])
            state = int(row["state"])
            cnt = int(row["cnt"])
            if blk not in mosq_per_block:
                mosq_per_block[blk] = {"susceptible": 0, "exposed": 0, "infected": 0, "total": 0}
            key = {0: "susceptible", 1: "exposed", 2: "infected"}.get(state, "susceptible")
            mosq_per_block[blk][key] += cnt
            mosq_per_block[blk]["total"] += cnt
        d["mosquitoes_per_block"] = mosq_per_block
        d["total_mosquitoes"] = sum(v["total"] for v in mosq_per_block.values())
        d["total_infected_mosquitoes"] = sum(v["infected"] for v in mosq_per_block.values())

        ppl_per_block = {}
        for _, row in people_df.iterrows():
            blk = int(row["living_place"])
            state = int(row["state"])
            cnt = int(row["cnt"])
            if blk not in ppl_per_block:
                ppl_per_block[blk] = {"susceptible": 0, "infected": 0, "recovered": 0, "total": 0}
            key = {0: "susceptible", 1: "infected", 2: "recovered"}.get(state, "susceptible")
            ppl_per_block[blk][key] += cnt
            ppl_per_block[blk]["total"] += cnt
        d["people_per_block"] = ppl_per_block
        d["total_people"] = sum(v["total"] for v in ppl_per_block.values())

        bs_per_block = {}
        for _, row in bs_df.iterrows():
            blk = int(row["curr_building"])
            bs_per_block[blk] = int(row["cnt"])
        d["breeding_sites_per_block"] = bs_per_block
        d["total_breeding_sites"] = sum(bs_per_block.values())
        d["total_eggs"] = int(eggs_df.iloc[0]["cnt"]) if not eggs_df.empty else 0

        logger.info(f"[DEBUG] Initial scenario: {d['total_people']} people, {d['total_mosquitoes']} mosquitoes, "
                     f"{d['total_breeding_sites']} BS, {d['total_eggs']} eggs, {d['total_initial_infected_people']} real infected")

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
                [binary_path, input_graph, max_time_route, str(self._alpha), socket_str],
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
        time.sleep(10)
        
    def _reset_socket(self):
        self._socket.close()
        self._socket = self._context.socket(zmq.REQ)
        self._socket.connect(self._socket_str)
        self._socket.setsockopt(zmq.RCVTIMEO, self._socket_default_timeout)
        self._socket.setsockopt(zmq.LINGER, 0)

    def _call_optimization(self, action: str = "run") -> Solution | None:
        message = action
        if action == "load":
            message += f":{self._run_id}"
        if action == "run":
            message += f":{self._objective_function}"

        timeout = self._socket_run_timeout if action == "run" else self._socket_default_timeout
        self._socket.setsockopt(zmq.RCVTIMEO, timeout)

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
                self._reset_socket()
                self._socket.setsockopt(zmq.RCVTIMEO, timeout)
                time.sleep(self._socket_retry_interval)
            except zmq.ZMQError as e:
                logger.error(f"[!] ZMQ Error: {e}")
                self._reset_socket()
                self._socket.setsockopt(zmq.RCVTIMEO, timeout)
                time.sleep(self._socket_retry_interval)

        logger.error("[!] Failed to receive response from optimization after multiple attempts.")
        return None

    def _call_naive_optimization(self):
        speed_m_per_s: float = 10000 / 3600  # 10 km/h in m/s
        valid_mask = getattr(self, "_valid_block_mask", None)

        candidate_blocks: List[int] = [
            b for b in range(self._graph.b)
            if (valid_mask is None or valid_mask[b])
        ]

        avg_cases_per_block: List[float] = [0.0] * self._graph.b
        for block in candidate_blocks:
            avg_cases_per_block[block] = self._infected_per_block[block]

        sorted_blocks_by_avg_cases: List[int] = sorted(
            candidate_blocks,
            key=lambda b: avg_cases_per_block[b],
            reverse=True
        )

        block_visiting_time = 0.0
        visited_blocks = []
        for block in sorted_blocks_by_avg_cases:
            arcs: List = self._graph.block_arcs[block]
            total_length_meters = sum(arc.length for arc in arcs)
            total_time_seconds = total_length_meters / speed_m_per_s if speed_m_per_s > 0 else 0
            if total_time_seconds + block_visiting_time > 3600:
                break
            block_visiting_time += total_time_seconds
            visited_blocks.append(block)

        time.sleep(1)
        logger.info(f"[*] Naive optimization solution: {len(visited_blocks)} blocks with total time {block_visiting_time:.2f} seconds")
        solution = Solution(visited_blocks, 0.0, 0.0)
        self._evaluate_deterministic_solution(solution)
        return solution

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
        
        if solution.get_deterministic_of() <= 0.0:
            deterministic_of = 0.0
            for b in solution.get_blocks():
                deterministic_of += self._infected_per_block[b]
            solution.set_deterministic_of(deterministic_of)

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
            avoided_cases: float = 0

            for block, cases in enumerate(scenario):
                total_cases += cases

                if block in solution_blocks:
                    avoided_cases += cases

            if avoided_cases > 0:
                stochastic_of += ((avoided_cases * self._alpha)/total_cases)

        return stochastic_of

    def _call_simulation(self, max_cycles: int, is_batch: bool = False, is_short: bool = True, nebulize_solution: int = -1):
        logger.info("[*] Running Simulation...")
        start_date = self._get_run_param("end_date")

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
        ).drop_duplicates(subset=["id", "simulation_id"])

        b = self._graph.b

        if sim_cases.empty:
            logger.warning("[!] No simulation cases found, returning single zero scenario.")
            return [[0] * b]

        grouped = sim_cases.groupby(
            ["living_place", "simulation_id"], as_index=False
        ).count()

        if grouped.empty:
            logger.warning("[!] Grouped data is empty, returning single zero scenario.")
            return [[0] * b]

        num_scenarios = int(np.max(grouped["simulation_id"].unique()))

        all_scenarios = [
            grouped[grouped["simulation_id"] == s]
            .set_index("living_place")["id"]
            .reindex(range(b), fill_value=0)
            .tolist()
            for s in range(1, num_scenarios + 1)
        ]

        return all_scenarios

    def _delete_cases_from_run_id(self):
        self._db.query_remove(f"DELETE FROM metrics_infected_people WHERE execution_id = {self._run_id}")

    def _compute_metrics(self):
        pass

    def _compute_valid_block_mask(self) -> List[bool]:
        """Mark blocks whose lat/lon polygon is non-degenerate.

        GAML's `create_street_blocks_and_save` keeps only blocks where
        `envelope(polygon).area > 0`, so any optimizer choice on a
        degenerate block has no Building counterpart in GAML and used to
        crash `load_blocks_to_nebulize` with IndexOutOfBounds. We mirror
        that filter here (slightly stricter: actual polygon area, not
        envelope) so the optimizer never sees those blocks as attractive
        targets, and any leftover mismatch is absorbed by the GAML guard.
        """
        valid: List[bool] = [False] * self._graph.b
        for block_index in range(self._graph.b):
            if block_index not in self._graph.block_nodes:
                continue
            coords = [
                (self._graph.nodes[j].lon, self._graph.nodes[j].lat)
                for j in self._graph.block_nodes[block_index]
            ]
            if len(coords) < 3:
                continue
            try:
                poly = Polygon(coords)
                if poly.is_valid and poly.area > 0:
                    valid[block_index] = True
            except Exception as e:
                logger.debug(f"[valid-mask] Polygon failed for block {block_index}: {e}")
        return valid

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
        city, city_osm_name = Utils.get_city_info(city_key)
        map_size = self._get_run_param("map_size")
        start_date = self._get_run_param("start_date")
        end_date = self._get_run_param("end_date")

        logger.info(f"[*] Loading OSM map: {city_osm_name} ({map_size})...")
        osm = OpenStreetMap(city_osm_name, map_size)
        self._graph: Graph = MapAdapter.convert_osm_to_graph(osm, True)

        plot_path = MapAdapter.plot_region_map(
            map_data=osm.osm_map,
            output_dir=self._output_folder,
            filename="osm_region_validation.png",
            show=False,
        )
        logger.info(f"[*] OSM validation plot saved to: {plot_path}")

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

        self._valid_block_mask: List[bool] = self._compute_valid_block_mask()
        invalid_blocks_with_cases = [
            i for i, inf in enumerate(self._infected_per_block)
            if inf > 0 and not self._valid_block_mask[i]
        ]
        total_invalid = sum(1 for v in self._valid_block_mask if not v)
        if invalid_blocks_with_cases:
            dropped = sum(int(self._infected_per_block[i]) for i in invalid_blocks_with_cases)
            logger.warning(
                f"[!] Dropping {dropped} real cases from {len(invalid_blocks_with_cases)} blocks "
                f"with degenerate polygons (no Building counterpart in GAMA): "
                f"{invalid_blocks_with_cases[:20]}{'...' if len(invalid_blocks_with_cases) > 20 else ''}"
            )
            for i in invalid_blocks_with_cases:
                self._infected_per_block[i] = 0
        logger.info(
            f"[*] Valid blocks: {self._graph.b - total_invalid}/{self._graph.b} "
            f"(invalid/degenerate: {total_invalid})"
        )

        logger.info(f"[*]Starting Num. Infected: {self._infected_per_block}")
        self._write_graph(os.path.join(self._output_folder, "graph.txt"))

        logger.info("[*] Creating starting scenario into Database...")
        self._scenario_generator = ScenarioGeneration(
            execution_id=self._exec_id,
            simulation_id=0,
            cycle=0,
            started_from_cycle=0,
            start_date=end_date,
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

        self._debug_data["config"] = {
            "run_params": self._run_params,
            "sim_params": self._sim_params,
            "alpha": self._alpha,
            "stochastic_evaluation": self._stochastic_evaluation,
            "objective_function": self._objective_function,
        }
        self._collect_initial_scenario_debug()

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

        def stochastic_of_sort_key(x):
            if x["stochastic_of"] == "baseline":
                return float("-inf")
            try:
                if isinstance(x["stochastic_of"], str) and x["stochastic_of"].startswith("OF = "):
                    return float(x["stochastic_of"].replace("OF = ", ""))
                return float(x["stochastic_of"])
            except Exception:
                return float("inf")

        boxplot_data_sorted = sorted(boxplot_data, key=stochastic_of_sort_key)
        df = pd.DataFrame(boxplot_data_sorted)
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

    def mabs_naive_analysis(self):
        """Run naive analysis comparing base vs nebulized scenarios against real data."""

        # --- 1. Run nebulized scenario ---
        solution = self._elite_stochastic_solutions[0]
        self._run_id += 1
        self._db.run_query_insert_solution(self._run_id, solution.get_blocks())
        self._call_simulation(
            max_cycles=180,
            is_batch=True,
            is_short=False,
            nebulize_solution=self._run_id
        )

        # --- 2. Helpers ---
        def get_weekly_simulated_cases_all(run_id):
            """Return dict of weekly cases per simulation, list of weeks, and raw grouped dataframe."""
            df = self._db.query(f"""
                SELECT simulation_id, event_date
                FROM metrics_infected_people
                WHERE execution_id = {run_id}
            """)
            if df.empty:
                return {}, [], []

            df["event_date"] = pd.to_datetime(df["event_date"])
            df["week_str"] = df["event_date"].apply(
                lambda d: Utils.last_day_of_week(d).strftime("%Y-%m-%d")
            )
            df["simulation_id"] = df["simulation_id"].astype(str)

            grouped = df.groupby(["week_str", "simulation_id"]).size().reset_index(name="infected")
            weeks = sorted(grouped["week_str"].unique())

            week_to_cases = {
                week: grouped[grouped["week_str"] == week]["infected"].tolist()
                for week in weeks
            }
            return week_to_cases, weeks, grouped

        def plot_boxplot_with_style(ax, data, positions, color, label, hatch=None, box_linestyle='solid', median_linestyle='solid'):
            """Plot a styled boxplot with color and return its handle for the legend."""
            # Use black edge color for all, and hatching for distinction, and apply color
            bp = ax.boxplot(
                data,
                positions=positions,
                widths=0.35,
                patch_artist=True,
                medianprops=dict(color="black", linestyle=median_linestyle, linewidth=2),
                whiskerprops=dict(color="black", linestyle=box_linestyle),
                capprops=dict(color="black", linestyle=box_linestyle),
                boxprops=dict(linestyle=box_linestyle, color="black"),
                flierprops=dict(markerfacecolor="black", marker="o", markersize=3, alpha=0.3),
            )
            for patch in bp["boxes"]:
                patch.set(facecolor=color, edgecolor="black", alpha=1.0, linewidth=1.5, hatch=hatch)
            return Patch(facecolor=color, edgecolor="black", label=label, hatch=hatch)

        # --- 3. Get scenarios data ---
        base_cases, base_weeks, _ = get_weekly_simulated_cases_all(self._run_id - 1)
        nebu_cases, nebu_weeks, _ = get_weekly_simulated_cases_all(self._run_id)
        all_weeks = sorted(set(base_weeks) | set(nebu_weeks))

        # --- 4. Get real cases per week ---
        start_date = self._get_run_param("start_date")
        city_key = get_city_info(self._get_run_param("city"))[0]
        coord_blocks: List[Polygon] = Utils.all_blocks_as_polygons(self._graph)

        real_per_week = {}
        if city_key and coord_blocks:
            max_sim_date = max(all_weeks) if all_weeks else None
            if max_sim_date:
                df_real = self._db.get_notifications_between_dates(start_date, max_sim_date, city_key)
                if not df_real.empty:
                    df_real = df_real[
                        (df_real["classification"] != 5) &
                        df_real.apply(
                            lambda row: any(
                                poly.contains(Point(row["y"], row["x"])) for poly in coord_blocks
                            ),
                            axis=1,
                        )
                    ][["data_notification"]]
                    df_real["data_notification"] = pd.to_datetime(df_real["data_notification"])
                    df_real["week_str"] = df_real["data_notification"].apply(
                        lambda d: Utils.last_day_of_week(d).strftime("%Y-%m-%d")
                    )
                    real_per_week = df_real.groupby("week_str").size().to_dict()
        # --- 5. Prepare data series ---
        start_num_cases = np.sum(self._infected_per_block)
        real_cases_y = [start_num_cases] + [real_per_week.get(week, 0) for week in all_weeks[1:]]

        # Agrupar dados por semana
        weeks_sorted = [str(w) for w in all_weeks]
        week_indices = list(range(1, len(weeks_sorted) + 1))

        simulated_data = [[start_num_cases]]
        simulated_nebu_data = [[start_num_cases]]

        for week in all_weeks[1:]:
            simulated_data.append(base_cases.get(week, []))
            simulated_nebu_data.append(nebu_cases.get(week, []))

        # --- 6. Plot results ---
        plt.figure(figsize=(max(12, len(real_cases_y) * 0.8), 7))
        ax = plt.gca()

        # Boxplot positions
        box_width = 0.35
        pos_sim = [x - box_width / 2 for x in week_indices]
        pos_nebu = [x + box_width / 2 for x in week_indices]

        # Add boxplots with different hatches and linestyles for B&W distinction
        legend_handles = []
        legend_handles.append(
            plot_boxplot_with_style(
                ax, simulated_data, pos_sim, "#808080", "Simulated",
                hatch='o', box_linestyle='solid', median_linestyle='solid'
            )
        )
        legend_handles.append(
            plot_boxplot_with_style(
                ax, simulated_nebu_data, pos_nebu, "#008000", "Simulated With Nebulization",
                hatch='x', box_linestyle='dashed', median_linestyle='dashed'
            )
        )

        # Add real cases line (use black, solid line)
        ax.plot(
            week_indices,
            real_cases_y,
            label="Real Cases",
            marker="o",
            linestyle="-",
            color="black",
            linewidth=2
        )
        legend_handles.append(plt.Line2D([0], [0], color="black", marker="o", label="Real Cases", linewidth=2))

        # Axes labels and title
        ax.set_xlabel("Week")
        ax.set_ylabel("Number of Notifications")

        # X-ticks
        ax.set_xticks(week_indices)
        ax.set_xticklabels(week_indices)

        # Y-axis grid
        ax.yaxis.grid(True, which="major", linestyle="--", alpha=0.7)
        ax.yaxis.grid(True, which="minor", linestyle=":", alpha=0.3)
        ax.minorticks_on()

        # Legend
        ax.legend(handles=legend_handles)

        plt.tight_layout()
        plt.savefig(
            os.path.join(self._output_folder, "weekly_real_vs_simulated_cases_boxplot.pdf"),
            format="pdf", bbox_inches="tight"
        )
        plt.close()

    def _generate_debug_report(self):
        logger.info("[DEBUG] Generating debug HTML report...")
        d = self._debug_data
        ini = d["initial_scenario"]
        ra = d["risk_analysis"]
        cfg = d["config"]

        b = ini.get("total_blocks", 0)
        infected_per_block = ini.get("infected_per_block", [])
        mosq_per_block = ini.get("mosquitoes_per_block", {})
        ppl_per_block = ini.get("people_per_block", {})
        bs_per_block = ini.get("breeding_sites_per_block", {})

        all_solutions = ra.get("solutions", [])
        baseline = ra.get("baseline", {})

        def h(text):
            import html as html_mod
            return html_mod.escape(str(text))

        top_blocks_by_infected = sorted(
            range(len(infected_per_block)),
            key=lambda i: infected_per_block[i],
            reverse=True
        )[:30]

        # --- Build HTML ---
        parts = []
        parts.append("<!DOCTYPE html><html><head><meta charset='utf-8'>")
        parts.append("<title>Simheuristic Debug Report</title>")
        parts.append("<style>")
        parts.append("""
            body { font-family: 'Segoe UI', Arial, sans-serif; margin: 20px 40px; background: #f8f9fa; color: #212529; }
            h1 { color: #1a237e; border-bottom: 3px solid #1a237e; padding-bottom: 8px; }
            h2 { color: #283593; margin-top: 32px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
            h3 { color: #3949ab; }
            table { border-collapse: collapse; margin: 10px 0 20px 0; font-size: 13px; }
            th, td { border: 1px solid #ccc; padding: 5px 10px; text-align: right; }
            th { background: #e8eaf6; font-weight: 600; }
            tr:nth-child(even) { background: #f5f5f5; }
            .highlight { background: #fff9c4 !important; font-weight: bold; }
            .stat-box { display: inline-block; background: #e3f2fd; border-radius: 8px; padding: 12px 20px; margin: 6px; text-align: center; }
            .stat-box .val { font-size: 24px; font-weight: bold; color: #1565c0; }
            .stat-box .lbl { font-size: 12px; color: #555; }
            .warn { background: #fff3e0; border-left: 4px solid #ff9800; padding: 10px 16px; margin: 10px 0; }
            .info { background: #e3f2fd; border-left: 4px solid #1976d2; padding: 10px 16px; margin: 10px 0; }
            .diag { background: #fce4ec; border-left: 4px solid #c62828; padding: 10px 16px; margin: 10px 0; }
            .block-list { font-family: monospace; font-size: 12px; word-break: break-all; max-width: 800px; }
            .overlap-matrix td { text-align: center; min-width: 80px; }
        """)
        parts.append("</style></head><body>")

        # ===== 1. CONFIGURATION =====
        parts.append("<h1>Simheuristic Debug Report</h1>")
        parts.append("<h2>1. Configuration</h2>")
        parts.append("<table>")
        for section_name, section_data in [("Run Params", cfg.get("run_params", {})), ("Sim Params", cfg.get("sim_params", {}))]:
            for k, v in section_data.items():
                parts.append(f"<tr><th>{h(section_name)}</th><td>{h(k)}</td><td>{h(v)}</td></tr>")
        parts.append(f"<tr><th>Model</th><td>alpha</td><td>{cfg.get('alpha', '?')}</td></tr>")
        parts.append(f"<tr><th>Model</th><td>stochastic_evaluation</td><td>{cfg.get('stochastic_evaluation', '?')}</td></tr>")
        parts.append(f"<tr><th>Model</th><td>objective_function</td><td>{cfg.get('objective_function', '?')}</td></tr>")
        parts.append("</table>")

        # ===== 2. INITIAL SCENARIO =====
        parts.append("<h2>2. Initial Scenario</h2>")
        parts.append("<div>")
        for lbl, val in [
            ("Total Blocks", b),
            ("Total People", ini.get("total_people", 0)),
            ("Initial Infected (real cases)", ini.get("total_initial_infected_people", 0)),
            ("Total Mosquitoes", ini.get("total_mosquitoes", 0)),
            ("Infected Mosquitoes", ini.get("total_infected_mosquitoes", 0)),
            ("Total Breeding Sites", ini.get("total_breeding_sites", 0)),
            ("Total Eggs", ini.get("total_eggs", 0)),
        ]:
            parts.append(f"<div class='stat-box'><div class='val'>{val}</div><div class='lbl'>{lbl}</div></div>")
        parts.append("</div>")

        parts.append("<h3>Top 30 Blocks by Initial Real Infected Cases</h3>")
        parts.append("<table><tr><th>Block</th><th>Real Infected</th><th>People (total)</th>"
                     "<th>People (infected)</th><th>Mosquitoes (total)</th><th>Mosq. Infected</th>"
                     "<th>Breeding Sites</th></tr>")
        for blk in top_blocks_by_infected:
            inf = infected_per_block[blk] if blk < len(infected_per_block) else 0
            ppl = ppl_per_block.get(blk, {})
            mq = mosq_per_block.get(blk, {})
            bs = bs_per_block.get(blk, 0)
            cls = " class='highlight'" if inf > 0 else ""
            parts.append(f"<tr{cls}><td>{blk}</td><td>{inf}</td><td>{ppl.get('total',0)}</td>"
                         f"<td>{ppl.get('infected',0)}</td><td>{mq.get('total',0)}</td>"
                         f"<td>{mq.get('infected',0)}</td><td>{bs}</td></tr>")
        parts.append("</table>")

        blocks_with_infected = sum(1 for x in infected_per_block if x > 0)
        blocks_with_mosquitoes = sum(1 for v in mosq_per_block.values() if v.get("total", 0) > 0)
        parts.append(f"<div class='info'>Blocks with real infected cases: <b>{blocks_with_infected}</b> / {b} "
                     f"&mdash; Blocks with mosquitoes: <b>{blocks_with_mosquitoes}</b> / {b}</div>")

        # ===== 3. OPTIMIZATION RESULTS =====
        parts.append("<h2>3. Optimization Results</h2>")
        opt_iters = d.get("optimization_iterations", [])
        elite_count = sum(1 for it in opt_iters if it.get("is_elite"))
        parts.append(f"<div class='stat-box'><div class='val'>{len(opt_iters)}</div><div class='lbl'>Total Iterations</div></div>")
        parts.append(f"<div class='stat-box'><div class='val'>{elite_count}</div><div class='lbl'>Elite Solutions Found</div></div>")
        parts.append(f"<div class='stat-box'><div class='val'>{d.get('total_scenarios_accumulated', 0)}</div><div class='lbl'>Scenarios Accumulated</div></div>")

        parts.append("<h3>Final Elite Pool</h3>")
        elite_sols = d.get("elite_solutions", [])
        parts.append("<table><tr><th>#</th><th>Num Blocks</th><th>Det OF</th><th>Stochastic OF</th><th>Blocks</th></tr>")
        for i, es in enumerate(sorted(elite_sols, key=lambda x: x["stochastic_of"], reverse=True)):
            blocks_str = ", ".join(str(bl) for bl in sorted(es["blocks"]))
            parts.append(f"<tr><td>{i+1}</td><td>{es['num_blocks']}</td><td>{es['det_of']:.2f}</td>"
                         f"<td>{es['stochastic_of']:.4f}</td><td class='block-list'>{blocks_str}</td></tr>")
        parts.append("</table>")

        # ===== 4. SOLUTION COMPARISON =====
        parts.append("<h2>4. Solution Comparison (Naive vs Elites)</h2>")
        if all_solutions:
            naive_sol = all_solutions[0] if all_solutions[0]["id"] == "Naive" else None
            elite_list = [s for s in all_solutions if s["id"] != "Naive"]

            if naive_sol:
                naive_blocks_set = set(naive_sol["blocks"])
                parts.append(f"<h3>Naive Solution: {naive_sol['num_blocks']} blocks, "
                             f"Det OF = {naive_sol['det_of']:.2f}, Stochastic OF = {naive_sol['stochastic_of']:.4f}</h3>")
                parts.append(f"<div class='block-list'>Blocks: {sorted(naive_sol['blocks'])}</div>")

                parts.append("<h3>Overlap Matrix</h3>")
                parts.append("<table class='overlap-matrix'><tr><th>Solution</th><th>Num Blocks</th><th>Det OF</th>"
                             "<th>Stoch OF</th><th>Overlap w/ Naive</th><th>Only in This</th><th>Only in Naive</th></tr>")
                for es in elite_list:
                    es_set = set(es["blocks"])
                    overlap = naive_blocks_set & es_set
                    only_elite = es_set - naive_blocks_set
                    only_naive = naive_blocks_set - es_set
                    parts.append(f"<tr><td>{es['id']}</td><td>{es['num_blocks']}</td>"
                                 f"<td>{es['det_of']:.2f}</td><td>{es['stochastic_of']:.4f}</td>"
                                 f"<td>{len(overlap)}</td><td>{len(only_elite)}</td><td>{len(only_naive)}</td></tr>")
                parts.append("</table>")

                if elite_list:
                    parts.append("<h3>Per-Elite Block Detail</h3>")
                    for es in elite_list:
                        es_set = set(es["blocks"])
                        overlap = sorted(naive_blocks_set & es_set)
                        only_elite = sorted(es_set - naive_blocks_set)
                        only_naive = sorted(naive_blocks_set - es_set)
                        parts.append(f"<h4>{es['id']} ({es['num_blocks']} blocks)</h4>")
                        parts.append(f"<div class='block-list'><b>Overlapping blocks ({len(overlap)}):</b> {overlap}</div>")
                        parts.append(f"<div class='block-list'><b>Only in {es['id']} ({len(only_elite)}):</b> {only_elite}</div>")
                        parts.append(f"<div class='block-list'><b>Only in Naive ({len(only_naive)}):</b> {only_naive}</div>")

        # ===== 5. NEBULIZATION IMPACT ESTIMATE =====
        parts.append("<h2>5. Nebulization Impact Estimate</h2>")
        total_mosq = ini.get("total_mosquitoes", 0)
        if all_solutions and total_mosq > 0:
            parts.append("<table><tr><th>Solution</th><th>Blocks Nebulized</th><th>Mosquitoes in Nebulized Blocks</th>"
                         "<th>% of Total Mosquitoes</th><th>BS in Nebulized Blocks</th><th>% of Total BS</th></tr>")
            for sol in all_solutions:
                mosq_in_nebu = sum(mosq_per_block.get(bl, {}).get("total", 0) for bl in sol["blocks"])
                bs_in_nebu = sum(bs_per_block.get(bl, 0) for bl in sol["blocks"])
                pct_mosq = (mosq_in_nebu / total_mosq * 100) if total_mosq > 0 else 0
                total_bs = ini.get("total_breeding_sites", 1)
                pct_bs = (bs_in_nebu / total_bs * 100) if total_bs > 0 else 0
                parts.append(f"<tr><td>{sol['id']}</td><td>{sol['num_blocks']}</td>"
                             f"<td>{mosq_in_nebu}</td><td>{pct_mosq:.1f}%</td>"
                             f"<td>{bs_in_nebu}</td><td>{pct_bs:.1f}%</td></tr>")
            parts.append("</table>")

            parts.append("<div class='warn'><b>Model Limitation:</b> Nebulization in GAMA only kills adult mosquitoes at "
                         "simulation start (<code>load_starting_scenario</code>). Breeding sites and eggs in nebulized "
                         "blocks are NOT affected. Eggs hatch into new mosquitoes (rate = bs_eggs_to_mosquitoes = 0.125/cycle), "
                         "and breeding sites continue producing via oviposition. The mosquito population in nebulized blocks "
                         "recovers within a few cycles.</div>")
        else:
            parts.append("<div class='info'>No solution data available or no mosquitoes in initial scenario.</div>")

        # ===== 6. SIMULATION INFECTION RESULTS =====
        parts.append("<h2>6. Simulation Infection Results (14-cycle horizon)</h2>")
        initial_infected = ini.get("total_initial_infected_people", 0)

        parts.append("<h3>Summary Table</h3>")
        parts.append("<table><tr><th>Scenario</th><th>Num Blocks</th><th>Mean New Infections</th>"
                     "<th>Std</th><th>Min</th><th>Max</th><th>Median</th>"
                     "<th>% Change vs Baseline</th></tr>")

        baseline_mean = np.mean(baseline.get("scenario_sums", [0])) if baseline.get("scenario_sums") else 0

        def fmt_pct(val, ref):
            if ref == 0:
                return "N/A"
            pct = ((val - ref) / ref) * 100
            return f"{pct:+.1f}%"

        bl_sums = baseline.get("scenario_sums", [])
        if bl_sums:
            parts.append(f"<tr class='highlight'><td>Baseline</td><td>-</td>"
                         f"<td>{np.mean(bl_sums):.1f}</td><td>{np.std(bl_sums):.1f}</td>"
                         f"<td>{np.min(bl_sums)}</td><td>{np.max(bl_sums)}</td>"
                         f"<td>{np.median(bl_sums):.1f}</td><td>-</td></tr>")

        for sol in all_solutions:
            s_sums = sol.get("scenario_sums", [])
            if s_sums:
                s_mean = np.mean(s_sums)
                parts.append(f"<tr><td>{sol['id']}</td><td>{sol['num_blocks']}</td>"
                             f"<td>{s_mean:.1f}</td><td>{np.std(s_sums):.1f}</td>"
                             f"<td>{np.min(s_sums)}</td><td>{np.max(s_sums)}</td>"
                             f"<td>{np.median(s_sums):.1f}</td><td>{fmt_pct(s_mean, baseline_mean)}</td></tr>")
        parts.append("</table>")

        parts.append(f"<div class='info'><b>Note:</b> All values in the table above represent <b>new infections</b> "
                     f"during the 14-cycle (7-day) simulation horizon. GAMA only records people where "
                     f"<code>start_infected=false</code> in <code>metrics_infected_people</code>. "
                     f"Initial infected people from the starting scenario ({initial_infected}) are NOT counted.</div>")

        # Per-block top infections
        parts.append("<h3>Top 20 Blocks by Avg. New Infections (Baseline)</h3>")
        bl_avg = baseline.get("avg_infections_per_block", [])
        if bl_avg:
            sorted_bl = sorted(range(len(bl_avg)), key=lambda i: bl_avg[i], reverse=True)[:20]
            parts.append("<table><tr><th>Block</th><th>Avg Baseline Infections</th><th>Initial Real Infected</th>"
                         "<th>Initial Mosquitoes</th>")
            for sol in all_solutions:
                parts.append(f"<th>Avg {sol['id']} Infections</th><th>Nebulized?</th>")
            parts.append("</tr>")
            for blk in sorted_bl:
                bl_inf = bl_avg[blk] if blk < len(bl_avg) else 0
                real_inf = infected_per_block[blk] if blk < len(infected_per_block) else 0
                mosq_tot = mosq_per_block.get(blk, {}).get("total", 0)
                parts.append(f"<tr><td>{blk}</td><td>{bl_inf:.2f}</td><td>{real_inf}</td><td>{mosq_tot}</td>")
                for sol in all_solutions:
                    sol_avg = sol.get("avg_infections_per_block", [])
                    sol_val = sol_avg[blk] if blk < len(sol_avg) else 0
                    is_nebu = "Yes" if blk in sol["blocks"] else ""
                    parts.append(f"<td>{sol_val:.2f}</td><td>{is_nebu}</td>")
                parts.append("</tr>")
            parts.append("</table>")

        # ===== 7. ROOT CAUSE ANALYSIS =====
        parts.append("<h2>7. Root Cause Analysis</h2>")
        diagnostics = []

        if total_mosq > 0 and all_solutions:
            best_sol = max(all_solutions, key=lambda s: s["num_blocks"])
            mosq_in_best = sum(mosq_per_block.get(bl, {}).get("total", 0) for bl in best_sol["blocks"])
            pct = mosq_in_best / total_mosq * 100
            if pct < 30:
                diagnostics.append(
                    f"<div class='diag'><b>Low mosquito coverage:</b> The solution with most blocks ({best_sol['id']}, "
                    f"{best_sol['num_blocks']} blocks) only covers {mosq_in_best}/{total_mosq} mosquitoes "
                    f"({pct:.1f}%). Even with 100% kill efficiency, ~{100-pct:.0f}% of mosquitoes survive and continue "
                    f"the infection cycle.</div>"
                )

        total_bs_val = ini.get("total_breeding_sites", 0)
        if total_bs_val > 0 and all_solutions:
            best_sol = max(all_solutions, key=lambda s: s["num_blocks"])
            bs_in_best = sum(bs_per_block.get(bl, 0) for bl in best_sol["blocks"])
            pct_bs = bs_in_best / total_bs_val * 100
            diagnostics.append(
                f"<div class='diag'><b>Breeding sites untouched:</b> Nebulization does NOT deactivate breeding "
                f"sites or destroy eggs. In the best solution ({best_sol['id']}), {bs_in_best}/{total_bs_val} "
                f"BS ({pct_bs:.1f}%) are in nebulized blocks but remain active. Eggs continue hatching "
                f"(rate=0.125/cycle) and mosquitoes in remaining blocks oviposit (rate=0.02/cycle), "
                f"quickly replenishing the killed mosquitoes.</div>"
            )

        diagnostics.append(
            "<div class='diag'><b>Nebulization is a one-time event:</b> Mosquitoes are only killed during "
            "<code>load_starting_scenario</code> (cycle 0). After that, all 14 cycles run without any "
            "intervention. New mosquitoes born from eggs and oviposition are unaffected.</div>"
        )

        if bl_avg and all_solutions:
            baseline_top10 = sorted(range(len(bl_avg)), key=lambda i: bl_avg[i], reverse=True)[:10]
            for sol in all_solutions:
                sol_blocks_set = set(sol["blocks"])
                covered = sum(1 for blk in baseline_top10 if blk in sol_blocks_set)
                if covered < 5:
                    diagnostics.append(
                        f"<div class='warn'><b>Solution '{sol['id']}' misses top-infection blocks:</b> Only "
                        f"{covered}/10 of the blocks with highest baseline infections are nebulized by this solution. "
                        f"The optimization objective (deterministic OF from real cases) may not align well with "
                        f"where the simulation generates new infections.</div>"
                    )

        if baseline.get("scenario_sums") and all_solutions:
            bl_mean = np.mean(baseline["scenario_sums"])
            for sol in all_solutions:
                s_mean = np.mean(sol.get("scenario_sums", [0]))
                reduction = (bl_mean - s_mean) / bl_mean * 100 if bl_mean > 0 else 0
                if abs(reduction) < 5:
                    diagnostics.append(
                        f"<div class='warn'><b>Negligible reduction for {sol['id']}:</b> "
                        f"Mean new infections changed from {bl_mean:.1f} (baseline) to {s_mean:.1f} "
                        f"({reduction:+.1f}%). This suggests nebulizing adult mosquitoes alone has minimal "
                        f"impact on new infections over 14 cycles.</div>"
                    )

        if not diagnostics:
            diagnostics.append("<div class='info'>No specific diagnostics triggered.</div>")
        parts.extend(diagnostics)

        # ===== 8. GAMA MODEL PARAMETERS =====
        parts.append("<h2>8. GAMA Model Parameters (Reference)</h2>")
        gama_params = [
            ("step", "12 hours"), ("max_cycles", "14 (7 simulated days)"),
            ("nebulizer_efficiency", "1.0 (batch default)"), ("bs_insecticide_efficiency", "0.0 (unused)"),
            ("mosquitoes_death_rate", "0.01/cycle"), ("mosquitoes_oviposition_rate", "0.02/cycle"),
            ("bs_eggs_to_mosquitoes", "0.125/cycle"), ("bs_aquatic_phase_mortality_rate", "0.066/cycle"),
            ("mosquitoes_daily_rate_of_bites", "0.168"), ("mosquitoes_frac_infectious_bites", "0.6"),
            ("mosquitoes_susceptibility_to_dengue", "0.526"), ("mosquitoes_daily_latency_rate", "0.143"),
            ("people_daily_recovery_rate", "0.143"), ("mosquitoes_move_probability", "0.5 (batch default)"),
            ("max_move_radius", "50m"),
        ]
        parts.append("<table><tr><th>Parameter</th><th>Value</th></tr>")
        for name, val in gama_params:
            parts.append(f"<tr><td>{h(name)}</td><td>{h(val)}</td></tr>")
        parts.append("</table>")

        parts.append("</body></html>")

        report_path = os.path.join(self._output_folder, "debug_report.html")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(parts))
        logger.info(f"[DEBUG] Report saved to {report_path}")

    def risk_naive_analysis(self):
        boxplot_data = []
        stats_data = []
        ra = self._debug_data["risk_analysis"]
        ra["solutions"] = []

        # --- 1. Baseline (no nebulization) ---
        logger.info("[*] Risk Naive Analysis: Running baseline simulation...")
        self._run_id += 1
        self._call_simulation(max_cycles=14, is_batch=True, is_short=False)
        baseline_scenarios: List[List[int]] = self._get_scenario_cases_per_block()
        baseline_sums = [sum(s) for s in baseline_scenarios]

        avg_infections_per_block_baseline = np.mean(baseline_scenarios, axis=0).tolist() if baseline_scenarios else []
        ra["baseline"] = {
            "scenario_sums": baseline_sums,
            "avg_infections_per_block": avg_infections_per_block_baseline,
            "num_scenarios": len(baseline_scenarios),
        }

        baseline_avg = np.mean(baseline_sums)
        for cs in baseline_sums:
            boxplot_data.append({
                "label": f"Baseline\nAVG = {baseline_avg:.1f}",
                "value": cs,
                "type": "Baseline"
            })
        stats_data.append({
            "id": "Baseline",
            "min": np.min(baseline_sums),
            "max": np.max(baseline_sums),
            "avg": np.mean(baseline_sums),
            "std": np.std(baseline_sums),
            "deterministic_of": 0,
            "stochastic_of": 0.0,
            "blocks": ""
        })

        # --- 2. Naive solution (nebulized with naive heuristic) ---
        logger.info("[*] Risk Naive Analysis: Computing naive solution...")
        naive_solution = self._call_naive_optimization()
        self._delete_cases_from_run_id()
        self._run_id += 1
        simulation_id = self._run_id 
        self._db.run_query_insert_solution(simulation_id, naive_solution.get_blocks())
        self._call_simulation(max_cycles=14, is_batch=True, is_short=False, nebulize_solution=simulation_id)
        naive_scenarios: List[List[int]] = self._get_scenario_cases_per_block()
        naive_sums = [sum(s) for s in naive_scenarios]

        naive_stochastic_of = 0.0
        if self._stochastic_evaluation == "default":
            naive_stochastic_of = self._get_default_stochastic_value(naive_solution, naive_scenarios)
        elif self._stochastic_evaluation == "proportional":
            naive_stochastic_of = self._get_proportional_stochastic_value(naive_solution, naive_scenarios)
        naive_solution.set_stochastic_of(naive_stochastic_of)

        naive_avg = np.mean(naive_sums)
        for cs in naive_sums:
            boxplot_data.append({
                "label": f"Naive\nAVG = {naive_avg:.1f}",
                "value": cs,
                "type": "Naive"
            })
        stats_data.append({
            "id": "Naive",
            "min": np.min(naive_sums),
            "max": np.max(naive_sums),
            "avg": np.mean(naive_sums),
            "std": np.std(naive_sums),
            "deterministic_of": naive_solution.get_deterministic_of(),
            "stochastic_of": naive_stochastic_of,
            "blocks": ",".join(str(b) for b in naive_solution.get_blocks())
        })
        logger.info(f"[*] Naive — Det. OF: {naive_solution.get_deterministic_of()}, "
                     f"Stochastic OF: {round(naive_stochastic_of, 4)}")

        avg_infections_per_block_naive = np.mean(naive_scenarios, axis=0).tolist() if naive_scenarios else []
        ra["solutions"].append({
            "id": "Naive",
            "blocks": naive_solution.get_blocks(),
            "num_blocks": len(naive_solution.get_blocks()),
            "det_of": naive_solution.get_deterministic_of(),
            "stochastic_of": naive_stochastic_of,
            "scenario_sums": naive_sums,
            "avg_infections_per_block": avg_infections_per_block_naive,
        })

        sorted_elite = sorted(
            self._elite_stochastic_solutions,
            key=lambda s: s.get_stochastic_of(),
            reverse=True
        )

        for idx, solution in enumerate(sorted_elite):
            simulation_id += 1
            self._delete_cases_from_run_id()
            self._run_id += 1
            self._db.run_query_insert_solution(simulation_id, solution.get_blocks())
            self._call_simulation(max_cycles=14, is_batch=True, is_short=False, nebulize_solution=simulation_id)
            sol_scenarios: List[List[int]] = self._get_scenario_cases_per_block()
            sol_sums = [sum(s) for s in sol_scenarios]

            if self._stochastic_evaluation == "default":
                stochastic_of = self._get_default_stochastic_value(solution, sol_scenarios)
            elif self._stochastic_evaluation == "proportional":
                stochastic_of = self._get_proportional_stochastic_value(solution, sol_scenarios)
            
            solution.set_stochastic_of(stochastic_of)
            sol_avg = np.mean(sol_sums)
            sol_label = f"Elite {idx + 1}\nAVG = {sol_avg:.1f}"
            logger.info(f"[*] Risk Naive Analysis: Evaluating elite solution {idx + 1}/{len(sorted_elite)}, attending {len(solution.get_blocks())} blocks with Det. OF {solution.get_deterministic_of()} and Stochastic OF {round(solution.get_stochastic_of(), 4)}...")
            for cs in sol_sums:
                boxplot_data.append({
                    "label": sol_label,
                    "value": cs,
                    "type": "Elite"
                })
            stats_data.append({
                "id": f"Elite_{idx + 1}",
                "min": np.min(sol_sums),
                "max": np.max(sol_sums),
                "avg": np.mean(sol_sums),
                "std": np.std(sol_sums),
                "deterministic_of": solution.get_deterministic_of(),
                "stochastic_of": stochastic_of,
                "blocks": ",".join(str(b) for b in solution.get_blocks())
            })
            logger.info(f"[*] Elite {idx + 1} — Det. OF: {solution.get_deterministic_of()}, "
                         f"Stochastic OF: {round(stochastic_of, 4)}")

            avg_infections_per_block_elite = np.mean(sol_scenarios, axis=0).tolist() if sol_scenarios else []
            ra["solutions"].append({
                "id": f"Elite_{idx + 1}",
                "blocks": solution.get_blocks(),
                "num_blocks": len(solution.get_blocks()),
                "det_of": solution.get_deterministic_of(),
                "stochastic_of": stochastic_of,
                "scenario_sums": sol_sums,
                "avg_infections_per_block": avg_infections_per_block_elite,
            })

        # --- 4. Save stats ---
        stats_df = pd.DataFrame(stats_data)
        stats_path = os.path.join(self._output_folder, "risk_naive_analysis_stats.csv")
        stats_df.to_csv(stats_path, index=False)
        logger.info(f"[*] Saved stats to {stats_path}")

        # --- 5. Plot boxplot ---
        df = pd.DataFrame(boxplot_data)
        label_order = [f"Baseline\nAVG = {baseline_avg:.1f}"] + \
            [f"Naive\nAVG = {naive_avg:.1f}"] + \
            df[df["type"] == "Elite"]["label"].unique().tolist()

        num_columns = len(label_order)
        width = max(10, 2.5 * num_columns)
        fig, ax = plt.subplots(figsize=(width, 7))

        palette = {"Baseline": "#4C72B0", "Naive": "#DD8452", "Elite": "#55A868"}
        box_width = 0.5
        sns.boxplot(
            x="label",
            y="value",
            hue="type",
            data=df,
            order=label_order,
            hue_order=["Baseline", "Naive", "Elite"],
            palette=palette,
            dodge=False,
            width=box_width,
            ax=ax,
        )

        for i, lbl in enumerate(label_order):
            subset = df[df["label"] == lbl]["value"]
            q1 = subset.quantile(0.25)
            q3 = subset.quantile(0.75)
            iqr = q3 - q1
            median = subset.median()
            whisker_lo = subset[subset >= q1 - 1.5 * iqr].min()
            whisker_hi = subset[subset <= q3 + 1.5 * iqr].max()

            x_offset = box_width / 2 + 0.05
            ax.text(i + x_offset, median, f" {median:.1f}",
                    va="center", ha="left", fontsize=8, fontweight="bold")
            ax.text(i + x_offset, whisker_hi, f" {whisker_hi:.0f}",
                    va="bottom", ha="left", fontsize=7, color="#444444")
            ax.text(i + x_offset, whisker_lo, f" {whisker_lo:.0f}",
                    va="top", ha="left", fontsize=7, color="#444444")

        ax.set_xlabel("Solution")
        ax.set_ylabel("Total Cases per Scenario")
        ax.set_title("Risk Analysis: NoIntervention vs Naive vs Elite Solutions")
        ax.yaxis.grid(True, which="major", linestyle="--", alpha=0.7)
        ax.yaxis.grid(True, which="minor", linestyle=":", alpha=0.3)
        ax.minorticks_on()
        ax.legend(title="Algorithm")

        plt.tight_layout()
        plt.savefig(
            os.path.join(self._output_folder, "risk_naive_analysis_boxplot.png"),
            dpi=200, bbox_inches="tight"
        )
        plt.savefig(
            os.path.join(self._output_folder, "risk_naive_analysis_boxplot.pdf"),
            format="pdf", bbox_inches="tight"
        )
        plt.close()

        self._generate_debug_report()
        logger.info("[*] Risk Naive Analysis complete.")

    def run(self, socket_str: str, max_time_seconds: int = 120, elite_size: int = 10, max_iters_with_surrogate: int = 100):
        self._create_base_environment()
        self._start_optimization_executable()

        # Socket configuration
        self._socket_str = socket_str
        self._context = zmq.Context()
        self._socket_max_retries = 5
        self._socket_retry_interval = 2
        self._socket_default_timeout = 300  
        self._socket_run_timeout = 6000  
        self._socket = self._context.socket(zmq.REQ)
        self._socket.connect(self._socket_str)
        self._socket.setsockopt(zmq.RCVTIMEO, self._socket_default_timeout)
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

        self._debug_data["optimization_iterations"].append({
            "iteration": 0,
            "blocks": start_solution.get_blocks(),
            "num_blocks": len(start_solution.get_blocks()),
            "det_of": start_solution.get_deterministic_of(),
            "stochastic_of": start_solution.get_stochastic_of(),
            "is_elite": True,
        })

        logger.info("[*] Starting the First Stage...")
        start_time = time.time()
        elapsed_time: float = 0.0
        iterations = 0
        total_iterations = 0
        
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
    
            total_iterations += 1
            is_elite = stochastic_of > self._best_deterministic_solution.get_stochastic_of()

            self._debug_data["optimization_iterations"].append({
                "iteration": total_iterations,
                "blocks": new_det_solution.get_blocks(),
                "num_blocks": len(new_det_solution.get_blocks()),
                "det_of": new_det_solution.get_deterministic_of(),
                "stochastic_of": stochastic_of,
                "is_elite": is_elite,
            })

            if is_elite:
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

        self._debug_data["elite_solutions"] = [
            {"blocks": s.get_blocks(), "num_blocks": len(s.get_blocks()),
             "det_of": s.get_deterministic_of(), "stochastic_of": s.get_stochastic_of()}
            for s in self._elite_stochastic_solutions
        ]
        self._debug_data["total_scenarios_accumulated"] = len(self._scenarios)
        
        risk_start_time = time.time()
        # self.risk_analysis()
        self.risk_naive_analysis()
        logger.info(f"Risk analysis time: {time.time() - risk_start_time:.2f} seconds")

        # Clean up
        self._socket.close()    
        self._context.term()
            