from domain.node import Node

class Arc:
    def __init__(self, osmid: str, oneway: bool, name: str, length: float,
                 source: Node, target: Node, key: int, block: int = -1, cases: int = 0):
        self._block: int = block
        self._cases: int = cases
        self._osmid: str = osmid
        self._oneway: bool = oneway
        self._name: str = name
        self._length: float = length
        self._source: Node = source
        self._target: Node = target
        self._key: int = key

    @property
    def osmid(self):
        return self._osmid

    @property
    def osmid(self, value: str):
        self._osmid = value

    @property
    def oneway(self):
        return self._oneway

    @property
    def name(self):
        return self._name

    @property
    def length(self):
        return self._length

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, value):
        self._source = value

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, value):
        self._target = value

    @property
    def block(self):
        return self._block

    @block.setter
    def block(self, value):
        self._block = value

    @property
    def cases(self):
        return self._cases

    @cases.setter
    def cases(self, value):
        self._cases = value

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, value):
        self._key = value
