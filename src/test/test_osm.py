import os
import pytest
from adapters.osm.map_adapter import MapAdapter
from domain.graph import Graph
from domain.osm import OpenStreetMap


# test osm class
# @pytest.fixture
# def osm():
    # """Returns a empty Utils class"""
map_size = 15000
osm =  OpenStreetMap("Guaratiba, Rio de Janeiro, Brasil", map_size)
graph: Graph = MapAdapter.convert_osm_to_graph(osm, True)

path = os.path.abspath(f"./includes/GUARATIBA_{map_size}")
os.makedirs(path, exist_ok=True)

MapAdapter.export_osm_to_shapefile(osm, graph, path)

