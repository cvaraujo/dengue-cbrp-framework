import math
import logging, time
from typing import List
from shapely.geometry import Polygon
import domain.utils as Utils
from use_cases.simulation_metrics import SimulationMetrics
import sys, os
from domain.osm import OpenStreetMap
from domain.graph import Graph
from adapters.osm.map_adapter import MapAdapter
from datetime import datetime, timedelta
from adapters.sql.postgree import PostgreSQLAdapter
import numpy as np
import pandas as pd
from shapely.geometry import Point

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from use_cases.deterministic_instance import *
import logging
import osmnx as ox
from use_cases.experiments import *

ox.settings.use_cache = True
logging.basicConfig(level=logging.INFO)
# python3 -m venv .venv

def get_infected_people_per_block(df: pd.DataFrame, graph: Graph, coord_blocks: List[Polygon]):
    filtered_df = df[df["classification"] != 5]

    num_blocks = graph.b
    infected = np.zeros(num_blocks, dtype=int)

    for _, row in filtered_df.iterrows():
        y, x = float(row["y"]), float(row["x"])
        point: Point = Point(y, x)

        for i, polygon in enumerate(coord_blocks):
            if polygon.contains(point):
                infected[i] += 1

    return infected

def get_infected_simulated_people_per_block(df: pd.DataFrame, graph: Graph, coord_blocks: List[Polygon]):
    num_blocks = graph.b
    infected = np.zeros(num_blocks, dtype=int)

    # Group by living_place and sum the infected_people for each block
    df_aux = df.groupby("living_place")["infected_people"].mean().reset_index()
    df_aux["living_place"] = df_aux["living_place"].astype(int)
    df_aux["infected_people"] = df_aux["infected_people"].astype(float)

    for _, row in df_aux.iterrows():
        living_place = int(row["living_place"])
        if 0 <= living_place < num_blocks:
            infected[living_place] = int(row["infected_people"])
        else:
            logger.warning(f"living_place index {living_place} out of bounds for infected array of size {num_blocks}")

    return infected

def get_populational_parameters(city:str):
    """
        Gets the populational parameters for the given city in format "City name, State, Country".
        Returns:
            people_per_m2: float
            mosquitoes_per_person: float   
            nb_breeding_sites: int
            proportion_infected_mosquitoes_without_cases: float
            proportion_infected_mosquitoes_with_cases: float
    """    
    if city == "Alto Santo, Ceará, Brasil":
        return 0.01, 1.0, 50, 0.05, 0.4

    elif city == "Limoeiro do Norte, Ceará, Brasil":
        return 0.004, 1.0, 500, 0.2, 0.9

    else:
        return 0.001, 1.0, 50, 0.1, 0.5

def run_parameters_experiment():   
    output_folder: str = "/home/emily/Documentos/mestrado/simulation/dengue-cbrp-framework/experiments/"
    # output_folder: str = "/home/emily/Documentos/mestrado/simulation/dengue-cbrp-framework/experiments/"

    # Uncomment for Alto Santo    
    city: str = "Alto Santo, Ceará, Brasil"
    map_size: int = 700
    start_date: str = "2017-01-15"

    # Uncomment for Limoeiro do Norte
    #city: str = "Limoeiro do Norte, Ceará, Brasil"
    #map_size: int = 2000
    #start_date: str = "2020-07-19"

    output_folder += f"{city.split(',')[0].replace(' ','_')}-{start_date}/"
    os.makedirs(output_folder, exist_ok=True)
    
    logger.info(f"[*] Output folder: {output_folder}")

    (people_per_m2, 
    mosquitoes_per_person, 
    nb_breeding_sites, 
    proportion_infected_mosquitoes_without_cases, 
    proportion_infected_mosquitoes_with_cases) = get_populational_parameters(city)  
    
    experiments = Experiments(output_folder, 
                              city, 
                              map_size, 
                              start_date, 
                              people_per_m2, 
                              mosquitoes_per_person, 
                              nb_breeding_sites, 
                              proportion_infected_mosquitoes_without_cases, 
                              proportion_infected_mosquitoes_with_cases,
                              max_cycles=180)    
    
    logger.info("[*] Running experiments...")    
    #experiments.run_all()
    experiments.oviposition_experiment()

# python3 src/main.py simheuristic_runs/AS-20170108/ 2017-01-01 2017-01-08
def run_comparison_real_simulated():
    output_folder: str = "/home/emily/Documentos/mestrado/simulation/dengue-cbrp-framework/experiments/Guaratiba-2024-01-28/"
    # output_folder: str = sys.argv[1]
    os.makedirs(output_folder, exist_ok=True)
    
    # city: str = "Limoeiro do Norte, Ceará, Brasil"
    # city: str = "Alto Santo, Ceará, Brasil"
    city: str = "Guaratiba, Rio de Janeiro, Brasil"
    map_size: int = 0
    # logger.info(f"[*] Loading OSM map: {city} ({map_size})...")
    # osm: OpenStreetMap = OpenStreetMap(city, map_size)

    # graph: Graph = MapAdapter.convert_osm_to_graph(osm, True)
    # MapAdapter.export_osm_to_shapefile(osm, graph, f"{output_folder}/")

    # logger.info("[*] Retrieving dengue cases...")
    # start_date: str = "2017-01-15"
    start_date: str = "2024-01-28"
    # city_key: str = "LIMOEIRO"
    # start_datetime = datetime.strptime(start_date, "%Y-%m-%d")

    (people_per_m2, 
    mosquitoes_per_person, 
    nb_breeding_sites, 
    proportion_infected_mosquitoes_without_cases, 
    proportion_infected_mosquitoes_with_cases) = get_populational_parameters(city)    

    # db: PostgreSQLAdapter = PostgreSQLAdapter()

    # df = db.get_notifications_between_dates(
    #     start_date, (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=90)).strftime("%Y-%m-%d"), city_key
    # )

    # logger.info("[*] Processing blocks and population data...")
    # coord_blocks: List[Polygon] = Utils.all_blocks_as_polygons(graph)
    # infected = get_infected_people_per_block(df, graph, coord_blocks)
    # logger.info(f"Infected Real: {infected}")
    # osm.plot_map_with_cases(infected, f"{output_folder}/osm_map_real_cases.png")

    sim_metrics: SimulationMetrics = SimulationMetrics(output_folder=output_folder,
                                                       city=city,
                                                       max_cycles=90,
                                                        map_size=map_size,
                                                        start_date=start_date,
                                                        people_per_m2=people_per_m2,
                                                        mosquitoes_per_person=mosquitoes_per_person,
                                                        nb_breeding_sites=nb_breeding_sites,
                                                        proportion_infected_mosquitoes_without_cases=proportion_infected_mosquitoes_without_cases,
                                                        proportion_infected_mosquitoes_with_cases=proportion_infected_mosquitoes_with_cases,)
    
    logger.info("[*] Comparing simulated with real cases...")
    # sim_metrics.compare_simulated_with_real_cases(exec_id=1,clear_db=True, plot=True)
    sim_metrics.plot_min_max_avg_real(exec_id=1)

    # logger.info("[*] Processing simulated cases...")
    # df_sim = db.query(
    #     f"""
    #     SELECT simulation_id, living_place, count(id) as infected_people
    #     FROM metrics_infected_people
    #     WHERE execution_id = {1}
    #     GROUP BY simulation_id, living_place
    #     """
    # )

    # infected_sim = get_infected_simulated_people_per_block(df_sim, graph, coord_blocks)
    # logger.info(f"Infected Simulated: {infected_sim}")
    # # osm.plot_map_with_cases(infected_sim, f"{output_folder}/osm_map_sim_cases.png")

    # logger.info("[*] Calculating metrics...")
    # within_range_exact = 0
    # within_range_plus_minus_one = 0
    # within_range_plus_minus_one_without_zero = 0
    # total_infectes_geq_zero = 0
    # for block, cases in enumerate(infected):
    #     df_filt = df_sim[df_sim.living_place == block]
    #     if len(df_filt) > 0:
    #         min_sim = np.min(df_filt["infected_people"])
    #         max_sim = np.max(df_filt["infected_people"])
    #     else:
    #         min_sim = 0
    #         max_sim = 0

    #     within_range_exact += 1 if cases >= (min_sim) and cases <= (max_sim) else 0
    #     if cases > 0 or (min_sim == 0 and cases == 0):
    #         total_infectes_geq_zero += 1
    #         within_range_plus_minus_one += 1 if cases >= (min_sim) and cases <= (max_sim) else 0

    #     if cases == 0:
    #         within_range_plus_minus_one_without_zero += 1
    #     else:
    #         within_range_plus_minus_one_without_zero += 1 if cases >= (min_sim) and cases <= (max_sim) else 0

    # proportion_exact = ((within_range_exact / len(infected)) * 100)
    # proportion_excluding_outliers = ((within_range_plus_minus_one / total_infectes_geq_zero) * 100)
    # proportion_zero_cases = ((within_range_plus_minus_one_without_zero / len(infected)) * 100)

    # logger.info(f"Proportion of blocks (exact): {proportion_exact:.2f}%")
    # logger.info(f"Proportion of blocks (excluding outliers): {proportion_excluding_outliers:.2f}%")
    # logger.info(f"Proportion of blocks (zero cases): {proportion_zero_cases:.2f}%")

    # with open(f"{output_folder}/block_infected_proportions.txt", "w") as f:
    #     f.write(f"Proportion of blocks (exact): {proportion_exact:.2f}%\n")
    #     f.write(f"Proportion of blocks (excluding outliers): {proportion_excluding_outliers:.2f}%\n")
    #     f.write(f"Proportion of blocks (zero cases): {proportion_zero_cases:.2f}%\n")

    #     mask = (infected >= 0)
    #     if np.any(mask):
    #         mae = np.mean(np.abs(infected_sim[mask] - infected[mask]))
    #         f.write(f"Mean Absolute Error (MAE) between real and simulated cases per block: {mae:.2f}\n")
    #     else:
    #         f.write("MAE cannot be calculated: no real cases in any block.")


# run_parameters_experiment()
run_comparison_real_simulated()