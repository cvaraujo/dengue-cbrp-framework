class Arc:
    def __init__(self, osmid, oneway, name, length, source, target, key, block=-1):
        self._osmid = osmid
        self._oneway = oneway
        self._name = name
        self._length = length
        self._source = source
        self._target = target
        self._block = block
        self._cases = 0
        self._key = key

    @property
    def osmid(self):
        return self._osmid

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

    @property
    def target(self):
        return self._target

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
