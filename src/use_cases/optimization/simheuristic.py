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
    return "LIMOEIRO", "limoeiro"

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
        
    def _call_optimization(self, action: str = "run") -> Solution | None:
        message = action
        if action == "load":
            message += f":{self._run_id}"
        if action == "run":
            message += f":{self._objective_function}"

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

    def _call_naive_optimization(self):
        speed_m_per_s: float = 10000 / 3600  # 10 km/h in m/s
        avg_cases_per_block: List[float] = [0.0] * self._graph.b
        num_scenarios: int = len(self._scenarios)
        for block in range(self._graph.b):
            # block_cases: List[int] = [scenario[block] for scenario in self._scenarios]
            avg_cases_per_block[block] = self._infected_per_block[block] #sum(block_cases) / num_scenarios

        sorted_blocks_by_avg_cases: List[int] = sorted(
            range(self._graph.b),
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
        ).drop_duplicates(subset=["id"])

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
        print("Starting Num. Infected: ", self._infected_per_block)
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

    def clear_run(self):
        pass
        # self._db.clear_database()
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

    def risk_naive_analysis(self):
        boxplot_data = []
        stats_data = []

        # --- 1. Baseline (no nebulization) ---
        logger.info("[*] Risk Naive Analysis: Running baseline simulation...")
        self._run_id += 1
        self._call_simulation(max_cycles=14, is_batch=True, is_short=False)
        baseline_scenarios: List[List[int]] = self._get_scenario_cases_per_block()
        baseline_sums = [sum(s) for s in baseline_scenarios]

        for cs in baseline_sums:
            boxplot_data.append({
                "label": "Baseline",
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
        simulation_id = self._run_id + 1
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

        for cs in naive_sums:
            boxplot_data.append({
                "label": f"Naive\nOF={round(naive_solution.get_stochastic_of(), 4)}",
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

        sorted_elite = sorted(
            self._elite_stochastic_solutions,
            key=lambda s: s.get_stochastic_of(),
            reverse=True
        )

        for idx, solution in enumerate(sorted_elite):
            simulation_id += 1
            self._delete_cases_from_run_id()
            self._db.run_query_insert_solution(simulation_id, solution.get_blocks())
            self._call_simulation(max_cycles=14, is_batch=True, is_short=False, nebulize_solution=simulation_id)
            sol_scenarios: List[List[int]] = self._get_scenario_cases_per_block()
            sol_sums = [sum(s) for s in sol_scenarios]

            if self._stochastic_evaluation == "default":
                stochastic_of = self._get_default_stochastic_value(solution, sol_scenarios)
            elif self._stochastic_evaluation == "proportional":
                stochastic_of = self._get_proportional_stochastic_value(solution, sol_scenarios)
            
            solution.set_stochastic_of(stochastic_of)
            sol_label = f"Elite {idx + 1}\nOF={round(stochastic_of, 4)}"
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

        # --- 4. Save stats ---
        stats_df = pd.DataFrame(stats_data)
        stats_path = os.path.join(self._output_folder, "risk_naive_analysis_stats.csv")
        stats_df.to_csv(stats_path, index=False)
        logger.info(f"[*] Saved stats to {stats_path}")

        # --- 5. Plot boxplot ---
        df = pd.DataFrame(boxplot_data)
        label_order = ["Baseline"] + [f"Naive\nOF={round(naive_solution.get_stochastic_of(), 4)}"] + [
            f"Elite {i + 1}\nOF={round(s.get_stochastic_of(), 4)}"
            for i, s in enumerate(sorted_elite)
        ]

        num_columns = len(label_order)
        width = max(10, 2.5 * num_columns)
        fig, ax = plt.subplots(figsize=(width, 7))

        palette = {"Baseline": "#4C72B0", "Naive": "#DD8452", "Elite": "#55A868"}
        sns.boxplot(
            x="label",
            y="value",
            hue="type",
            data=df,
            order=label_order,
            hue_order=["Baseline", "Naive", "Elite"],
            palette=palette,
            dodge=False,
            width=0.5,
            ax=ax,
        )

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
        logger.info("[*] Risk Naive Analysis complete.")

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
        # self.risk_analysis()
        self.risk_naive_analysis()
        logger.info(f"Risk analysis time: {time.time() - risk_start_time:.2f} seconds")

        # Clean up
        self._socket.close()    
        self._context.term()
            