from typing import Set
from domain.arc import Arc


class Mosquito:
    def __init__(
        self,
        name: str,
        id: int,
        speed: float,
        state: int,
        current_road: Arc,
        start_outbreak: str,
        location: Set,
    ):
        self._name = name
        self._id = id
        self._speed = speed
        self._state = state
        self._current_road = current_road
        self._start_outbreak = start_outbreak
        self._location = location

    def get_all_attr(self):
        return [
            self._name,
            self._id,
            self._speed,
            self._state,
            self._current_road.key,
            self._start_outbreak.id,
            self._location,
        ]

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, value):
        self._speed = value

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

    @property
    def current_road(self):
        return self._current_road

    @current_road.setter
    def current_road(self, value):
        self._current_road = value

    @property
    def start_outbreak(self):
        return self._start_outbreak

    @start_outbreak.setter
    def start_outbreak(self, value):
        self._start_outbreak = value

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        self._location = value
