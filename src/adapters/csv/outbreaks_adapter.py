from domain.arc import Arc
from domain.outbreak import Outbreak
from domain.graph import Graph
import pandas as pd


class OutbreaksAdapter:
    def __init__(self):
        self._n = 0
        self._outbreaks = dict()

    def load_outbreaks_from_csv(self, graph: Graph, filename: str):
        try:
            df = pd.read_csv(filename, sep=";")
            for _, row in df.iterrows():
                id = row["id"]
                road_location = graph.get_edge_by_key(row["road_location.id_key"])
                new_outbreak = Outbreak(
                    row["name"],
                    id,
                    row["active"],
                    row["eggs"],
                    row["state"],
                    road_location,
                    (row["location.x"], row["location.y"]),
                )
                self._outbreaks[id] = new_outbreak
                self._n += 1
        except:
            return None

    def save_outbreaks_to_csv(self, filename: str):
        try:
            df = pd.DataFrame(
                columns=[
                    "name",
                    "id",
                    "active",
                    "eggs",
                    "road_location.id_key",
                    "location.x",
                    "location.y",
                ]
            )
            for outbreak in self._outbreaks.items():
                df.loc[len(df)] = outbreak.get_all_attr()
            df.to_csv(filename, sep=";")
        except:
            return None

    def update_outbreaks_from_csv(self, filename: str):
        try:
            df = pd.read_csv(filename, sep=";")
            for _, row in df.iterrows():
                # Get the Outbreak
                id = row["id"]
                outbreak = self._outbreaks[id]
                # Get the attributes that can change
                active = bool(row["active"])
                eggs = int(row["eggs"])
                # Change the attributes in the object
                outbreak.active = active
                outbreak.eggs = eggs
        except:
            return None

    def get_outbreak_by_id(self, id: int):
        return next(
            (outbreak for outbreak in self._outbreaks if outbreak.id == id), None
        )
