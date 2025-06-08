from use_cases.deterministic_instance import *
import logging, zmq, time
import osmnx as ox
from domain.osm import OpenStreetMap
from use_cases.simulation_metrics import SimulationMetrics
from adapters.osm.map_adapter import MapAdapter

# from use_cases.optimization.simheuristic import SimheuristicFramework

ox.settings.use_cache = True
logging.basicConfig(level=logging.INFO)
# python3 -m venv .venv

if __name__ == "__main__":
    city_name: str = "Limoeiro do Norte, Ceará, Brasil"
    map_size: int = 2000
    output_folder: str = "temp/simulation_metrics"
    run_params = {
        "city": city_name,
        "map_size": map_size,
        "start_date": "2017-01-08",
        "end_date": "2017-01-15",
    }

    sim_params = {
        "people_per_km2": 0.01,
        "mosquitoes_per_person": 1.25,
        "nb_breeding_sites": 50,
        "proportion_infected_mosquitoes_without_cases": 0.15,
        "proportion_infected_mosquitoes_with_cases": 0.45,
    }

    # sim = SimulationMetrics(output_folder)
    # sim.compare_simulated_with_real_cases(
    #     city_name, map_size, "2017-01-08", 0, 0.01, 1.0, 50, 0.05, 0.4, 180
    # )
    osm = OpenStreetMap(city_name, map_size)
    graph: Graph = MapAdapter.convert_osm_to_graph(osm, True)

    city_key, city_file = Utils.get_city_info(city_name)
    coord_blocks = Utils.all_blocks_as_polygons(graph)

    people_block = Utils.compute_people_per_block(graph, 0.0045, coord_blocks)
    print(f"Total people: {sum(people_block)}")
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
