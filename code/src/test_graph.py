import pytest
from model.md_graph import Graph


# test md_utils
@pytest.fixture
def graph():
    """Returns a empty Utils class"""
    return Graph()


def test_create_from_addr(graph):
    graph.create_graph_from_addr("Alto Santo, Ceará", 100)
    assert str(graph) == "7 nodes and 14 arcs"


def test_create_blocks(graph):
    graph.create_graph_from_addr("Alto Santo, Ceará", 200)
    graph.create_blocks()
    for i in graph.nodes:
        for j in graph.arcs[i.index]:
            assert j.block < 8
