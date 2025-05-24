import os
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


class StochasticInstanceGenerator:
    def __init__(self, output_folder: str):
        self.output_folder = output_folder
        self.db = PostgreSQLAdapter()

    def _build_shapefile_path(self, city_key: str, map_size: int) -> str:
        path = os.path.abspath(f"./includes/{city_key}_{map_size}")
        os.makedirs(path, exist_ok=True)
        return path

    def _prepare_parameters(
        self, shp_path, exec_id, start_date, max_cycles, save_states
    ):
        return {
            "sqlite_ds": ("string", ""),
            "max_cycles": ("int", max_cycles),
            "default_shp_dir": ("string", shp_path),
            "use_initial_scenario": ("bool", True),
            "start_from_cycle": ("int", 0),
            "start_from_scenario": ("int", 0),
            "start_from_execution_id": ("int", exec_id),
            "start_date_str": ("string", start_date),
            "execution_id": ("int", exec_id),
            "save_states": ("bool", save_states),
        }

    def _write_instance(self, graph: Graph, filename: str, infected_per_block):
        with open(filename, "w") as file:
            # Header
            file.write(f"{graph.n} {graph.m} {graph.b}\n")

            # Nodes
            for id, node in graph.nodes.items():
                blocks = ",".join(str(b) for b in node.get_blocks())
                file.write(f"N {id} {node.lat:.6f} {node.lon:.6f} {blocks}\n")

            # Arcs
            for idx in range(graph.n):
                for arc in graph.arcs[idx]:
                    block = -1 if arc.block == -1 else arc.block
                    file.write(
                        f"A {arc.source.index} {arc.target.index} {arc.length:.3f} {block}\n"
                    )

            # Infected per block
            for i, infected in enumerate(infected_per_block):
                if infected > 0:
                    file.write(f"B {i} {infected}\n")

    def _write_prob_from_scenarios(
        self, scenarios: List, graph: Graph, output_name: str
    ):
        """
        Write scenarios to a file with probabilities and case counts per block.

        Args:
            scenarios (list of list of int): Matrix [scenario][block] with number of cases.
            graph: base Graph.
            output_name (str): path to output file.
        """
        num_scenarios = len(scenarios)

        with open(output_name, "w") as file:
            file.write(f"{num_scenarios}\n")

            for i, scenario in enumerate(scenarios):
                file.write(f"P {i} {1.0 / num_scenarios:.3f}\n")

                for b in range(graph.b):
                    count = scenario[b]
                    if count > 0:
                        file.write(f"B {i} {b} {count}\n")
                    elif count < 0:
                        raise ValueError(
                            f"[!] Block {b} in scenario {i} has a negative number of cases"
                        )

    def generate(
        self,
        city: str,
        map_size: int,
        start_date: str,
        end_date: str,
        exec_id: int,
        people_per_km2: float,
        num_scenarios: int,
    ):
        logger.info("[*] Clearing data from database...")
        self.db.clear_database()

        logger.info(f"[*] Loading OSM map: {city} ({map_size})...")
        osm = OpenStreetMap(city, map_size)
        graph: Graph = MapAdapter.convert_osm_to_graph(osm, True)

        logger.info("[*] Retrieving dengue cases...")
        city_key, city_file = Utils.get_city_info(city)
        cases = self.db.get_notifications_between_dates(start_date, end_date, city_key)

        logger.info("[*] Processing blocks and population data...")
        coord_blocks = Utils.all_blocks_as_polygons(graph)
        people_block = Utils.compute_people_per_block(graph, people_per_km2)
        infected, recovered = Utils.get_infected_recovered_people_per_block(
            cases, graph, datetime.strptime(start_date, "%Y-%m-%d"), coord_blocks
        )

        logger.info("[*] Inserting starting scenario...")
        sg: ScenarioGeneration = ScenarioGeneration(
            execution_id=exec_id,
            simulation_id=0,
            cycle=0,
            started_from_cycle=0,
            start_date=start_date,
            connection=self.db,
        )

        sg.create_starting_scenario(
            people_per_block=people_block,
            infected_people_per_block=infected,
            recovered_people_per_block=recovered,
            mosquitoes_per_person=1.5,
            nb_breeding_sites=30,
            proportion_infected_mosquitoes_without_cases=0.2,
            proportion_infected_mosquitoes_with_cases=0.8,
        )

        logger.info("[*] Exporting SHP files...")
        shp_path = self._build_shapefile_path(city_key, map_size)
        MapAdapter.export_osm_to_shapefile(osm, graph, shp_path)

        logger.info("[*] Running initial simulation...")
        params = self._prepare_parameters(
            shp_path, exec_id, start_date, max_cycles=0, save_states=False
        )

        sim: Simulation = Simulation()
        sim.run_simulation(JsonAdapter.convert_param_2_list(params), is_batch=False)

        logger.info("[*] Running batch simulation...")
        params = self._prepare_parameters(
            shp_path, exec_id, start_date, max_cycles=14, save_states=True
        )
        sim.run_simulation(JsonAdapter.convert_param_2_list(params), is_batch=True)

        logger.info("[*] Exporting instance...")
        instance_file = os.path.join(
            self.output_folder, f"{city_file}-{map_size}-{exec_id}.txt"
        )
        self._write_instance(graph, instance_file, infected)

        logger.info("[*] Extracting and aggregating simulated cases...")
        sim_cases = self.db.query(
            f"SELECT * FROM metrics_infected_people WHERE execution_id = {exec_id}"
        ).drop_duplicates(subset=["id"])

        grouped = sim_cases.groupby(
            ["living_place", "simulation_id"], as_index=False
        ).count()

        all_scenarios = [
            grouped[grouped["simulation_id"] == s]
            .set_index("living_place")["id"]
            .reindex(range(graph.b), fill_value=0)
            .tolist()
            for s in range(1, num_scenarios + 1)
        ]

        logger.info("[*] Saving scenario probabilities...")
        scenario_file = os.path.join(
            self.output_folder, f"scenarios-{city_file}-{map_size}-{exec_id}.txt"
        )
        self._write_prob_from_scenarios(all_scenarios, graph, scenario_file)

        self.db.clear_database()
        # self.db.close_all_idle_connections()
        self.db.close()
        logger.info("[*] Stochastic instance generation completed.")
