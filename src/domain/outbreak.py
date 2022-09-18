from typing import Set
from domain.arc import Arc


class Outbreak:
    def __init__(
        self,
        name: str,
        id: int,
        active: bool,
        eggs: int,
        road_location: Arc,
        location: Set,
    ):
        self._name = name
        self._id = id
        self._active = active
        self._eggs = eggs
        self._road_location = road_location
        self._location = location

    def get_all_attr(self):
        return [
            self._name,
            self._id,
            self._active,
            self._eggs,
            self._road_location.key,
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
    def active(self):
        return self._active

    @active.setter
    def active(self, value):
        self._active = value

    @property
    def eggs(self):
        return self._eggs

    @eggs.setter
    def eggs(self, value):
        self._eggs = value

    @property
    def road_location(self):
        return self._road_location

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        self._location = value
