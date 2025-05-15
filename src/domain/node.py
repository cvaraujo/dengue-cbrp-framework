from typing import Set

class Node:
    def __init__(self, osmid: str, index: int, lat: float, lon: float):
        self._osmid: str = osmid
        self._index: int = index
        self._lat: float = lat
        self._lon: float = lon
        self._blocks: Set[int] = set()

    def get_blocks(self) -> Set[int]:
        return self._blocks if self._blocks else {-1}

    def add_block(self, block_num: int):
        self._blocks.add(block_num)

    @property
    def blocks(self):
        return self._blocks

    @property
    def osmid(self, value):
        self._osmid = value

    @property
    def osmid(self):
        return self._osmid

    @property
    def index(self):
        return self._index

    @property
    def lat(self):
        return self._lat

    @property
    def lon(self):
        return self._lon

    @property
    def block(self):
        return self._block if len(self._block) > 0 else [-1]

    @block.setter
    def block(self, value):
        self._block = value
