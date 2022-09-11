import pytest
from domain.osm import OpenStreetMap


# test osm class
@pytest.fixture
def osm():
    """Returns a empty Utils class"""
    return OpenStreetMap("Alto Santo, Ceará", 100)


def test_load_map(osm):
    osm.load_map()


def test_plot(osm):
    osm.load_map()
    # assert osm.plot_map() is not None


def test_add_edge_key_attribute(osm):
    osm.load_map()
    osm.add_edge_key_attribute()
