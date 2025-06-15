from use_cases.deterministic_instance import *
import logging, os, subprocess
from use_cases.optimization.simheuristic import SimheuristicFramework

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# python3 -m venv .venv

if __name__ == "__main__":
    city_name: str = "Alto Santo, Ceará, Brasil"
    map_size: int = 700
    output_folder: str = "temp/simulation_metrics"
    run_params = {
        "city": city_name,
        "map_size": map_size,
        "start_date": "2017-01-08",
        "end_date": "2017-01-15",
    }

    sim_params = {
        "people_per_km2": 0.008,
        "mosquitoes_per_person": 0.5,
        "nb_breeding_sites": 10,
        "proportion_infected_mosquitoes_without_cases": 0.15,
        "proportion_infected_mosquitoes_with_cases": 0.45,
    }


    socket_str = "tcp://localhost:6969"
    opt_params = {
        "project_dir": "/home/carlos/Documentos/cbrp-methodologies/",
        "executable_path": "/home/carlos/Documentos/cbrp-methodologies/cbrp-simheur",
        "socket_str": socket_str
    }


    max_time_seconds = 30
    elite_size = 5 
    max_iters_with_surrogate = 10
    
    sh = SimheuristicFramework(output_folder, run_params, sim_params, opt_params)
    sh.run(socket_str, max_time_seconds, elite_size, max_iters_with_surrogate)
    sh.clear_run()

    # sim = SimulationMetrics(output_folder)
    # sim.compare_simulated_with_real_cases(
    #     city_name, map_size, "2017-01-08", 0, 0.01, 1.0, 50, 0.05, 0.4, 180
    # )

    # infected, recovered = Utils.get_infected_recovered_people_per_block(
    #     cases, graph, datetime.strptime(start_date, "%Y-%m-%d"), coord_blocks
    # )

    # context = zmq.Context()
    # socket = context.socket(zmq.REQ)
    # socket.connect("tcp://localhost:6969")

    # while True:
    #     exec_id = input("Enter execution ID to send: ")
    #     message = f"id:{exec_id}"
    #     socket.send_string(message)
    #     print(f"📨 Sent: {message}")

    #     # Aguarda resposta
    #     reply = socket.recv_string()
    #     print(f"✅ Received reply: {reply}")

    # os.makedirs(output_folder, exist_ok=True)
    # sh = SimheuristicFramework(output_folder, run_params, sim_params, {})
    # sh.run()
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
