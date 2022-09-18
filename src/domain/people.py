from typing import Set
from domain.arc import Arc


class People:
    def __init__(
        self,
        name: str,
        id: int,
        objective: str,
        speed: float,
        state: int,
        living_place: Arc,
        working_place: Arc,
        start_work: int,
        end_work: int,
        location: Set,
    ):
        self._name = name
        self._id = id
        self._objective = objective
        self._speed = speed
        self._state = state
        self._living_place = living_place
        self._working_place = working_place
        self._start_work = start_work
        self._end_work = end_work
        self._location = location

    def get_all_attr(self):
        return [
            self._name,
            self._id,
            self._objective,
            self._speed,
            self._state,
            self._living_place.key,
            self._working_place.key,
            self._start_work,
            self._end_work,
            self._location[0],
            self._location[1],
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
    def objective(self):
        return self._objective

    @objective.setter
    def objective(self, value):
        self._objective = value

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
    def living_place(self):
        return self._living_place

    @living_place.setter
    def living_place(self, value):
        self._living_place = value

    @property
    def working_place(self):
        return self._working_place

    @working_place.setter
    def working_place(self, value):
        self._working_place = value

    @property
    def start_work(self):
        return self._start_work

    @start_work.setter
    def start_work(self, value):
        self._start_work = value

    @property
    def end_work(self):
        return self._end_work

    @end_work.setter
    def end_work(self, value):
        self._end_work = value

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        self._location = value
