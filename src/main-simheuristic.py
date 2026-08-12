from use_cases.deterministic_instance import *
import logging, time
from use_cases.optimization.simheuristic import SimheuristicFramework
from use_cases.simulation import Simulation
import sys
from itertools import product

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

default_as_sim_params = {
    "people_per_km2": 0.01,
    "mosquitoes_per_person": 1.0,
    "nb_breeding_sites": 50,
    "proportion_infected_mosquitoes_without_cases": 0.05,
    "proportion_infected_mosquitoes_with_cases": 0.4,
    "num_scenarios_evaluation": 20,
}

default_lm_sim_params = {
    "people_per_km2": 0.004,
    "mosquitoes_per_person": 1.0,
    "nb_breeding_sites": 300,
    "proportion_infected_mosquitoes_without_cases": 0.2,
    "proportion_infected_mosquitoes_with_cases": 0.9,
    "num_scenarios_evaluation": 20,
}

default_gt_sim_params = {
    "people_per_km2": 0.00117, 
    "mosquitoes_per_person": 0.5,
    "nb_breeding_sites": 720,
    "proportion_infected_mosquitoes_without_cases": 0.125,
    "proportion_infected_mosquitoes_with_cases": 0.5,
    "num_scenarios_evaluation": 20,
}

city_info_map = {
    "AS": "Alto Santo, Ceará, Brasil",
    "LM": "Limoeiro do Norte, Ceará, Brasil",
    "GT": "Guaratiba, Rio de Janeiro, Brasil",
}

default_connection_params = {
    "local": {
        "socket_str": "tcp://localhost:2021",
        "project_dir": "/home/carlos/Documentos/cbrp-methodologies",
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

BATCH_DATES = {
    # "LM": [
    #     ("2020-06-28", "2020-07-05"),
    #     ("2020-07-05", "2020-07-12"),
    #     ("2020-07-19", "2020-07-26"),
    #     ("2020-07-05", "2020-07-26"),
    #     ("2024-01-28", "2024-02-03"), #  Emily
    # ],
    "GT": [
        ("2024-02-26", "2024-03-03"), #  gráfico
    #  ("2024-01-28", "2024-02-03"), #  Emily
       
    ]
}

BATCH_PARAMS = {
    "alphas": [0.8],
    "map_sizes": [2000,3000,3500],
    "max_iters_with_surrogate": [100],
    "runtime": 120,
    "elite_size": 5,
    "stochastic_evaluation": "default",
    "objective_function": "FULL",
    "default_route_time": "1200",
}


def run_single_experiment(
    run_mode, city, map_size, start_date, end_date, alpha,
    max_run_time, elite_size, max_iters, stochastic_evaluation,
    objective_function, output_folder, default_route_time="1200"
):
    if city == "AS":
        sim_params = default_as_sim_params
    elif city == "LM":
        sim_params = default_lm_sim_params
    elif city == "GT":
        sim_params = default_gt_sim_params
    else:
        logger.warning(f"Cidade {city} não reconhecida. Usando parâmetros padrão de Limoeiro.")
        sim_params = default_lm_sim_params
    city_name = city_info_map.get(city, "Guaratiba, Rio de Janeiro, Brasil")
    conn = default_connection_params[run_mode] if run_mode in default_connection_params else default_connection_params["docker"]

    run_params = {
        "city": city_name,
        "map_size": map_size,
        "start_date": start_date,
        "end_date": end_date,
    }
    opt_params = {
        "project_dir": conn["project_dir"],
        "executable_path": conn["executable_path"],
        "socket_str": conn["socket_str"],
        "max_time_route": default_route_time,
    }

    os.makedirs(output_folder, exist_ok=True)

    start_time = time.time()
    simulation = Simulation(conn["server_path"], conn["server_port"], conn["model"])
    simheuristic = SimheuristicFramework(
        output_folder, run_params, sim_params, opt_params, simulation,
        alpha_model=alpha, stochastic_evaluation=stochastic_evaluation,
        objective_function=objective_function,
    )

    simheuristic.run(conn["socket_str"], max_run_time, elite_size, max_iters)
    elapsed = time.time() - start_time
    logger.info(f"Experiment finished in {elapsed:.2f}s -> {output_folder}")
    simheuristic.clear_run()


def run_batch(run_mode, base_output):
    cities = list(BATCH_DATES.keys())
    alphas = BATCH_PARAMS["alphas"]
    map_sizes = BATCH_PARAMS["map_sizes"]
    iters_list = BATCH_PARAMS["max_iters_with_surrogate"]
    runtime = BATCH_PARAMS["runtime"]
    elite_size = BATCH_PARAMS["elite_size"]
    stochastic_eval = BATCH_PARAMS["stochastic_evaluation"]
    obj_func = BATCH_PARAMS["objective_function"]
    route_time = BATCH_PARAMS["default_route_time"]

    experiments = []
    for city in cities:
        for (start_date, end_date) in BATCH_DATES[city]:
            for map_size, alpha, max_iters in product(map_sizes, alphas, iters_list):
                folder_name = (
                    f"{city}_{start_date}_map{map_size}"
                    f"_alpha{alpha}_iters{max_iters}"
                )
                output_folder = os.path.join(base_output, city, folder_name)
                experiments.append({
                    "city": city,
                    "map_size": map_size,
                    "start_date": start_date,
                    "end_date": end_date,
                    "alpha": alpha,
                    "max_iters": max_iters,
                    "output_folder": output_folder,
                })

    total = len(experiments)
    logger.info(f"=== BATCH MODE: {total} experiments to run ===")
    batch_start = time.time()

    for i, exp in enumerate(experiments, 1):
        logger.info(
            f"=== [{i}/{total}] {exp['city']} | {exp['start_date']} | "
            f"map={exp['map_size']} | alpha={exp['alpha']} | iters={exp['max_iters']} ==="
        )
        try:
            run_single_experiment(
                run_mode=run_mode,
                city=exp["city"],
                map_size=exp["map_size"],
                start_date=exp["start_date"],
                end_date=exp["end_date"],
                alpha=exp["alpha"],
                max_run_time=runtime,
                elite_size=elite_size,
                max_iters=exp["max_iters"],
                stochastic_evaluation=stochastic_eval,
                objective_function=obj_func,
                output_folder=exp["output_folder"],
                default_route_time=route_time,
            )
        except Exception as e:
            logger.error(f"=== FAILED [{i}/{total}]: {e} ===", exc_info=True)

    total_time = time.time() - batch_start
    logger.info(f"=== BATCH COMPLETE: {total} experiments in {total_time:.2f}s ===")


# Single run:
#   python3 src/main-simheuristic.py docker default 600 5 500 AS 1000 2017-01-08 2017-01-15 /app/output/
#
# Batch run:
#   python3 src/main-simheuristic.py batch docker /app/simheuristic_runs
#   python3 src/main-simheuristic.py batch local /home/carlos/Documentos/dengue-cbrp-framework/simheuristic_runs

if __name__ == "__main__":
    args = sys.argv

    if len(args) > 1 and args[1] == "batch":
        run_mode = args[2] if len(args) > 2 else "docker"
        base_output = args[3] if len(args) > 3 else "/app/simheuristic_runs"
        run_batch(run_mode, base_output)

    elif len(args) > 1:
        run_mode = args[1]
        stochastic_evaluation = args[2]
        max_run_time = int(args[3])
        elite_size = int(args[4])
        max_iters_with_surrogate = int(args[5])
        city = args[6]
        map_size = int(args[7])
        start_date = args[8]
        end_date = args[9]
        output_folder = args[10]

        run_single_experiment(
            run_mode=run_mode,
            city=city,
            map_size=map_size,
            start_date=start_date,
            end_date=end_date,
            alpha=0.8,
            max_run_time=max_run_time,
            elite_size=elite_size,
            max_iters=max_iters_with_surrogate,
            stochastic_evaluation=stochastic_evaluation,
            objective_function="FULL",
            output_folder=output_folder,
        )

    else:
        logger.info("Usage:")
        logger.info("  Batch:  python3 src/main-simheuristic.py batch <local|docker> <output_base_dir>")
        logger.info("  Single: python3 src/main-simheuristic.py <local|docker> <eval> <time> <elite> <iters> <city> <map> <start> <end> <output>")
