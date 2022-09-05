class Node:
    def __init__(self, osmid, index, lat, lon):
        self._osmid = osmid
        self._index = index
        self._lat = lat
        self._lon = lon
        self._block = set()

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

    def add_block(self, b):
        self._block.add(b)
