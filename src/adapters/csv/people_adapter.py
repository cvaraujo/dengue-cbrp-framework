from domain.arc import Arc
from domain.people import People
from domain.graph import Graph
import pandas as pd


class PeopleAdapter:
    def __init__(self):
        self._n = 0
        self._people = dict()

    def load_people_from_csv(self, graph: Graph, filename: str):
        try:
            df = pd.read_csv(filename, sep=";")
            for _, row in df.iterrows():
                id = row["id"]
                living_place = graph.get_edge_by_key(row["living_place.id_key"])
                working_place = graph.get_edge_by_key(row["working_place.id_key"])
                new_people = People(
                    row["name"],
                    id,
                    row["objective"],
                    row["speed"],
                    row["state"],
                    living_place,
                    working_place,
                    row["start_work"],
                    row["end_work"],
                    (row["location.x"], row["location.y"]),
                )
                self._people[id] = new_people
                self._n += 1
        except:
            return None

    def save_people_to_csv(self, filename: str):
        try:
            df = pd.DataFrame(
                columns=[
                    "name",
                    "id",
                    "objective",
                    "speed",
                    "state",
                    "living_place.id_key",
                    "working_place.id_key",
                    "start_work",
                    "end_work",
                    "location.x",
                    "location.y",
                ]
            )
            for people in self._people.items():
                df.loc[len(df)] = people.get_all_attr()
            df.to_csv(filename, sep=";")
        except:
            return None

    def update_people_from_csv(self, filename: str):
        try:
            df = pd.read_csv(filename, sep=";")
            for _, row in df.iterrows():
                # Get the Person
                id = row["id"]
                people = self._people[id]
                # Get the attributes that can change
                state = int(row["state"])
                objective = row["objective"]
                location = (row["location.x"], row["location.y"])
                # Change the attributes in the object
                people.state = state
                people.objective = objective
                people.location = location
        except:
            return None
