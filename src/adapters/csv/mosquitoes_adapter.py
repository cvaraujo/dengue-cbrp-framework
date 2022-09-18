from domain.arc import Arc
from adapters.csv.outbreaks_adapter import OutbreaksAdapter
from domain.graph import Graph
from domain.mosquito import Mosquito
from domain.outbreak import Outbreak
import pandas as pd


class MosquitoesAdapter:
    def __init__(self):
        self._n = 0
        self._mosquitoes = dict()
        self._selected_outbreaks = dict()

    def load_mosquitoes_from_csv(
        self, graph: Graph, outbreaks: OutbreaksAdapter, filename: str
    ):
        try:
            df = pd.read_csv(filename, sep=";")

            for _, row in df.iterrows():
                id = row["id"]
                current_road = graph.get_edge_by_key(row["current_road.id_key"])
                outbreak_id = row["start_outbreak.id"]

                # Check if the outbreak_id exists
                if outbreak_id in self._selected_outbreaks:
                    outbreak = self._selected_outbreaks[outbreak_id]
                else:
                    outbreak = outbreaks.get_outbreak_by_id(outbreak_id)
                    self._selected_outbreaks[outbreak_id] = outbreak

                new_mosquito = Mosquito(
                    row["name"],
                    id,
                    row["speed"],
                    row["state"],
                    current_road,
                    outbreak,
                    (row["location.x"], row["location.y"]),
                )
                self._mosquitoes[id] = new_mosquito
                self._n += 1
        except:
            return None

    def save_mosquitoes_to_csv(self, filename: str):
        try:
            df = pd.DataFrame(
                columns=[
                    "name",
                    "id",
                    "speed",
                    "state",
                    "current_road.id_key",
                    "start_outbreak.id",
                    "location.x",
                    "location.y",
                ]
            )
            for mosquito in self._mosquitoes.items():
                df.loc[len(df)] = mosquito.get_all_attr()
            df.to_csv(filename, sep=";")
        except:
            return None

    def update_mosquitoes_from_csv(self, graph: Graph, filename: str):
        try:
            df = pd.read_csv(filename, sep=";")
            for _, row in df.iterrows():
                # Get the Person
                id = row["id"]
                current_road = graph.get_edge_by_key(row["current_road.id_key"])
                if id in self._mosquitoes:
                    mosquito = self._mosquitoes[id]
                    # Get the attributes that can change
                    state = int(row["state"])

                    location = (row["location.x"], row["location.y"])
                    # Change the attributes in the object
                    mosquito.state = state
                    mosquito.current_road = current_road
                    mosquito.location = location
                else:
                    outbreak_id = row["start_outbreak.id"]

                    # Check if the outbreak_id exists
                    if outbreak_id in self._selected_outbreaks:
                        outbreak = self._selected_outbreaks[outbreak_id]
                    else:
                        outbreak = outbreaks.get_outbreak_by_id(outbreak_id)
                        self._selected_outbreaks[outbreak_id] = outbreak

                    new_mosquito = Mosquito(
                        row["name"],
                        id,
                        row["speed"],
                        row["state"],
                        current_road,
                        outbreak,
                        (row["location.x"], row["location.y"]),
                    )
                    self._mosquitoes[id] = new_mosquito
                    self._n += 1
        except:
            return None
