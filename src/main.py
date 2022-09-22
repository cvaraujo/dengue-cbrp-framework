from os import path
from user_cases.simulation import Simulation
from adapters.osm.map_adapter import MapToGraph
from domain.osm import OpenStreetMap
from domain.graph import Graph


if __name__ == "__main__":
    # OpenStreetMap
    osm = OpenStreetMap("Alto Santo, Ceará", 500)
    osm.load_map()
    osm.add_edge_key_attribute()

    MapToGraph().export_osm_to_shapefile(osm, path.abspath("temp/shp/as"))

    simulation = Simulation(
        "0",
        10,
        5,
        10,
        5,
        5,
        "temp/shp/as",
        "dengue_propagation",
        1,
    )

    simulation.run()
