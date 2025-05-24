import os
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


class SimheuristicFramework:
    def __init__(
        self,
        output_folder: str,
        run_params: dict,
        simulation_params: dict,
        optimization_params: dict,
    ):
        self._output_folder = output_folder
        self._sim_params = simulation_params
        self._opt_params = optimization_params
        self._run_params = run_params
        self._exec_id = 0
        self._simulation = Simulation()
        self._db = PostgreSQLAdapter()

    def _get_sim_param(self, param_key: str):
        try:
            param = self._sim_params[param_key]
            return param
        except KeyError:
            logger.warning(f"[!] Simulation parameter {param_key} not found!")

    def _get_opt_param(self, param_key: str):
        try:
            param = self._sim_params[param_key]
            return param
        except KeyError:
            logger.warning(f"[!] Optimization parameter {param_key} not found!")

    def _get_run_param(self, param_key: str):
        try:
            param = self._run_params[param_key]
            return param
        except KeyError:
            logger.warning(f"[!] Run parameter {param_key} not found!")

    def _call_optimization(self):
        pass

    def _call_parallel_optimization(self):
        pass

    def _call_simulation(self, max_cycles: int, is_batch: bool = False):
        logger.info("[*] Running Simulation...")
        start_date = self._get_run_param("start_date")

        params = Utils.prepare_parameters(
            self._shp_path,
            self._exec_id,
            start_date,
            max_cycles=max_cycles,
            save_states=is_batch,
        )

        header = JsonAdapter.convert_param_2_list(params)
        self._simulation.run_simulation(header, is_batch=is_batch)

    def _call_short_simulation(self):
        self._call_simulation(14, is_batch=True)

    def _call_extensive_simulation(self):
        # Call simulation several times and append results before call again
        self._call_simulation(14, is_batch=True)

    def _get_scenario_cases_per_block(self) -> List[List[int]]:
        logger.info("[*] Extracting and aggregating simulated cases...")
        sim_cases = self._db.query(
            f"SELECT * FROM metrics_infected_people WHERE execution_id = {self._exec_id}"
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

    def _write_scenarios_2_optimization(self, scenarios: List):
        num_scenarios = len(scenarios)
        map_size = self._get_run_param("map_size")
        city_key = self._get_run_param("city")
        _, city_file = Utils.get_city_info(city_key)

        scenario_file = os.path.join(
            self._output_folder, f"scenarios-{city_file}-{map_size}-{self._exec_id}.txt"
        )

        B = self._graph.b
        prob_scn: float = 1.0 / num_scenarios
        with open(scenario_file, "w") as file:
            file.write(f"{num_scenarios}\n")

            for i, scenario in enumerate(scenarios):
                file.write(f"P {i} {prob_scn:.3f}\n")

                for b in range(B):
                    count = scenario[b]
                    if count > 0:
                        file.write(f"B {i} {b} {count}\n")
                    elif count < 0:
                        raise ValueError(
                            f"[!] Block {b} in scenario {i} has a negative number of cases"
                        )

    def _write_scenarios(self):
        scenarios = self._get_scenario_cases_per_block()
        self._write_scenarios_2_optimization(scenarios)

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

    def _create_base_solution(self):
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
        people_block = Utils.compute_people_per_block(self._graph, people_per_km2)
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

    def run(self):
        self._create_base_solution()
        self._write_graph(os.path.join(self._output_folder, "graph.txt"))
        self._call_short_simulation()
        # self._write_scenarios()

    def clear_run(self):
        self._db.clear_database()
        self._simulation.kill_gama_headless()
