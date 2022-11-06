import os
from pathlib import Path
from domain.graph import Graph
from use_cases.simulation import Simulation
from adapters.csv.mosquitoes_adapter import MosquitoesAdapter
from adapters.csv.outbreaks_adapter import OutbreaksAdapter
from adapters.csv.people_adapter import PeopleAdapter


class InstanceGenerator:
    def __init__(
        self,
        graph: Graph,
        simulation: Simulation,
        mosquitoes: MosquitoesAdapter = None,
        outbreaks: OutbreaksAdapter = None,
        people: PeopleAdapter = None,
        verbose=True,
    ):
        self._graph = graph
        self._simulation = simulation
        self._mosquitoes = mosquitoes
        self._outbreaks = outbreaks
        self._people = people
        self.verbose = verbose

    def generate_single_scenarios(
        self,
        num_cycles: int,
        folder_name=os.path.abspath("../../data/single_scenarios"),
    ):
        # Create the directory
        Path(folder_name).mkdir(parents=True, exist_ok=True)

        # Start the simulation
        self._simulation.id = 0
        for i in range(num_cycles):
            self._simulation.run()

    def generate_multi_scenarios(self):
        pass

    def generate_online_scenarios(self):
        pass
