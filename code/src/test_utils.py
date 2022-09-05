import pytest
from model.md_utils import Utils
from model.md_graph import Graph


# test md_utils
@pytest.fixture
def utils():
    """Returns a empty Utils class"""
    return Utils()


def test_clockwise_angle(utils):
    assert utils.clockwise_angle([0, 0], [1, 1]) == 0.7853981633974483
