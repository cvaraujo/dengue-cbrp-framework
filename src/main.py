from use_cases.simulation import Simulation
from use_cases.instance_generator import InstanceGenerator
from adapters.osm.map_adapter import MapAdapter
from domain.osm import OpenStreetMap
from domain.graph import Graph
import logging
import osmnx as ox
from os import path
import networkx as nx

ox.settings.use_cache = True
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    # OpenStreetMap
    osm_map = OpenStreetMap("Limoeiro do Norte, Ceará", 300)
    # Graph
    graph = MapAdapter.convert_osm_to_graph(osm_map)
    # Shapefile
    shp_folder = path.abspath("temp/shp/as")
    MapAdapter.export_osm_to_shapefile(osm_map, shp_folder)
    # Simulation
    simulation = Simulation(
        50,
        10,
        200,
        200,
        50,
        shp_folder,
        "dengue_propagation",
        1,
        output_folder=path.abspath("temp/first_test"),
    )
    # Instance Generator
    inst_gen = InstanceGenerator(graph, simulation)
    inst_gen.generate_single_scenarios(10)

    # MapAdapter.write_graph_to_txt(graph, path.abspath("temp/limoeiro-500.txt"))

    # G = nx.Graph()
    # for node in g.nodes:
    #     G.add_node(node.index, pos=(node.lon, node.lat))
    # for i in range(g.n):
    #     for arc in g.arcs[i]:
    #         G.add_edge(arc.source, arc.target)
    # nx.draw(G, nx.get_node_attributes(G, "pos"), with_labels=True)

    # g.create_blocks()
    # g.plot_graph()
    # MapAdapter.write_graph_to_txt(g, path.abspath("temp/t1.txt"))

    # Get SHP from map
    # MapToGraph().export_osm_to_shapefile(osm, path.abspath("temp/shp/as"))

    # # Create the simulation

    # # Run
    # for _ in range(2):
    #     simulation.run()

    # Clear environment
    # simulation.clear()
