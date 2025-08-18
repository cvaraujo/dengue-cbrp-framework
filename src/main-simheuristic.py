from use_cases.deterministic_instance import *
import logging, time
from use_cases.optimization.simheuristic import SimheuristicFramework
from use_cases.simulation import Simulation
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# python3 -m venv .venv

default_as_sim_params = {
    "people_per_km2": 0.01,
    "mosquitoes_per_person": 1.0,
    "nb_breeding_sites": 50,
    "proportion_infected_mosquitoes_without_cases": 0.05,
    "proportion_infected_mosquitoes_with_cases": 0.4,
    "num_scenarios_evaluation": 20,
}

default_lm_sim_params = {
    "people_per_km2": 0.006,
    "mosquitoes_per_person": 0.8,
    "nb_breeding_sites": 300,
    "proportion_infected_mosquitoes_without_cases": 0.2,
    "proportion_infected_mosquitoes_with_cases": 0.9,
    "num_scenarios_evaluation": 20,
}

city_info_map = {
    "AS": "Alto Santo, Ceará, Brasil",
    "LM": "Limoeiro do Norte, Ceará, Brasil",
}

default_connection_params = {
    "local": {
        "socket_str": "tcp://localhost:2021",
        "project_dir": "/home/carlos/Documentos/cbrp-methodologies/",
        "executable_path": "/home/carlos/Documentos/cbrp-methodologies/cbrp-simheur",
        "server_path": "/home/carlos/Documentos/GAMA_1.9.2_Linux_with_JDK/headless/gama-headless.sh",
        "server_port": "6868",
        "model": "/home/carlos/Documentos/dengue-cbrp-framework/simulation/models/dengue_propagation.gaml",
    },
    "docker": {
        "socket_str": "tcp://0.0.0.0:2021",
        "project_dir": "/external-libs/simheuristic/cbrp-simheuristic/",
        "executable_path": "/external-libs/simheuristic/cbrp-simheuristic/cbrp-simheur",
        "server_path": "/external-libs/gama/headless/gama-headless.sh",
        "server_port": "6868",
        "model": "/app/simulation/models/dengue_propagation.gaml",
    }
}

# local run example: 
# python3 src/main.py local default 20 10 500 AS 700 2017-01-08 2017-01-15 /home/carlos/Documentos/dengue-cbrp-framework/simheuristic_runs/run_DEFAULT_10_500_AS_700_2017-01-08_2017-01-15/

# Docker run example: 
# python3 src/main.py docker default 1800 10 500 AS 700 2017-01-08 2017-01-15 /app/run_DEFAULT_10_500_AS_700_2017-01-08_2017-01-15/

if __name__ == "__main__":
    args = sys.argv
    run_mode = "local"
    default_route_time = "1200"
    max_run_time = 1800
    elite_size = 10
    max_iters_with_surrogate = 500
    city = "AS"
    map_size = 700
    start_date = "2017-01-08"
    end_date = "2017-01-15"
    output_folder = "/home/carlos/Documentos/dengue-cbrp-framework/temp/simulation_metrics"
    stochastic_evaluation = "default"

    if len(args) > 1:
        run_mode = args[1] # local or docker
        # Simheuristic parameters
        stochastic_evaluation = args[2] # default or proportional
        max_run_time = int(args[3]) # 1800
        elite_size = int(args[4]) # 10
        max_iters_with_surrogate = int(args[5]) # 500
        # Simulation/City parameters
        city = args[6] # AS or LM
        map_size = int(args[7]) # 700
        start_date = args[8] # 2017-01-08
        end_date = args[9] # 2017-01-15
        output_folder = args[10] # temp/simulation_metrics

    if not os.path.exists(output_folder):
        os.makedirs(output_folder, exist_ok=True)

    if city == "AS":
        sim_params = default_as_sim_params
    else:
        sim_params = default_lm_sim_params
    
    city_name = city_info_map.get(city, "Alto Santo, Ceará, Brasil")

    run_params = {
        "city": city_name,
        "map_size": map_size,
        "start_date": start_date,
        "end_date": end_date,
    }

    if run_mode == "local":
        connection_params = default_connection_params["local"]
    else:
        connection_params = default_connection_params["docker"]

    socket_str = connection_params["socket_str"]
    project_dir = connection_params["project_dir"]
    executable_path = connection_params["executable_path"]
    opt_params = {
        "project_dir": project_dir,
        "executable_path": executable_path,
        "socket_str": socket_str,
        "max_time_route": default_route_time
    }

    server_path = connection_params["server_path"]
    server_port = connection_params["server_port"]
    model = connection_params["model"]
    
    start_time = time.time()
    simulation = Simulation(server_path, server_port, model)
    simheuristic = SimheuristicFramework(output_folder, run_params, sim_params, opt_params, simulation, stochastic_evaluation)
    
    simheuristic.run(socket_str, max_run_time, elite_size, max_iters_with_surrogate)
    logger.info(f"Total time: {time.time() - start_time:.2f} seconds")
    simheuristic.clear_run()
