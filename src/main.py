from os import path
from use_cases.simulation import Simulation
from adapters.osm.map_adapter import MapAdapter
from domain.osm import OpenStreetMap
from domain.graph import Graph
import logging
import osmnx as ox
import warnings
import networkx as nx

ox.settings.use_cache = True
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    # OpenStreetMap
    osm = OpenStreetMap("Alto Santo, Ceará", 500)

    # Get SHP from map
    MapToGraph().export_osm_to_shapefile(osm, path.abspath("temp/shp/as"))

    # Create the simulation
    simulation = Simulation(
        10,
        5,
        10,
        5,
        5,
        "temp/shp/as",
        "dengue_propagation",
        1,
    )

    # Run
    for _ in range(2):
        simulation.run()

    # Clear environment
    # simulation.clear()
