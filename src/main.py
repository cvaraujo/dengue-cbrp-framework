from use_cases.deterministic_instance import *
import logging
import osmnx as ox
from use_cases.optimization.simheuristic import SimheuristicFramework

ox.settings.use_cache = True
logging.basicConfig(level=logging.INFO)
# python3 -m venv .venv

if __name__ == "__main__":
    city_name: str = "Alto Santo, Ceará, Brasil"
    map_size: int = 700
    output_folder: str = "temp/simheuristic/"
    run_params = {
        "city": city_name,
        "map_size": map_size,
        "start_date": "2017-01-08",
        "end_date": "2017-01-15",
    }

    sim_params = {
        "people_per_km2": 0.013,
        "mosquitoes_per_person": 1.0,
        "nb_breeding_sites": 50,
        "proportion_infected_mosquitoes_without_cases": 0.05,
        "proportion_infected_mosquitoes_with_cases": 0.4,
    }

    os.makedirs(output_folder, exist_ok=True)
    sh = SimheuristicFramework(output_folder, run_params, sim_params, {})
    sh.run()
    # si = SimulationMetrics(output_folder)
    # si.compare_simulated_with_real_cases(
    #     city_name,
    #     map_size,
    #     "2017-01-08",
    #     0,
    #     0.013,
    #     mosquitoes_per_person=1.0,
    #     nb_breeding_sites=50,
    #     proportion_infected_mosquitoes_without_cases=0.05,
    #     proportion_infected_mosquitoes_with_cases=0.4,
    #     max_cycles=180,
    #     plot=True,
    # )
