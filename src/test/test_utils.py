import pytest
from domain.utils import Utils
from domain.graph import Graph


# test utils
@pytest.fixture
def utils():
    """Returns a empty Utils class"""
    return Utils()


def test_clockwise_angle(utils):
    assert utils.clockwise_angle([0, 0], [1, 1]) == 0.7853981633974483
