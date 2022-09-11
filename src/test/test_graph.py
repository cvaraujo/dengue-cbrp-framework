import pytest
from domain.graph import Graph
from domain.osm import OpenStreetMap
from adapters.osm.map_to_graph import MapToGraph


# test graph
@pytest.fixture
def graph():
    """Returns a empty Utils class"""
    return Graph()


@pytest.fixture
def osm():
    """Returns a Alto Santo with 100 radius OSM class"""
    return OpenStreetMap("Alto Santo, Ceará", 100)


def test_osm_graph_conversion(osm):
    osm.load_map()
    assert MapToGraph.convert_osm_to_graph(osm) is not None


def test_create_blocks(osm):
    osm.load_map()
    graph = MapToGraph().convert_osm_to_graph(osm)

    if graph is not None:
        graph.create_blocks()

    assert graph.b == 1
