from typing import List, Dict
import math
import logging
from adapters.sql.postgree import PostgreSQLAdapter
from adapters.sql.queries import *


class ScenarioGeneration:
    def __init__(
        self,
        execution_id: int,
        simulation_id: int,
        cycle: int,
        started_from_cycle: int,
        start_date: str,
        connection: PostgreSQLAdapter,
    ):
        self._execution_id = execution_id
        self._simulation_id = simulation_id
        self._cycle = cycle
        self._started_from_cycle = started_from_cycle
        self._start_date = start_date
        self._connection = connection

    def _get_default_people_to_query(self, id_people: int, i: int, state: int) -> Dict:
        return {
            "execution_id": self._execution_id,
            "simulation_id": self._simulation_id,
            "cycle": self._cycle,
            "started_from_cycle": self._started_from_cycle,
            "name": f"People{id_people}",
            "id": id_people,
            "date_of_birth": self._start_date,
            "objective": "resting",
            "speed": -1.0,
            "state": state,
            "living_place": i,
            "working_place": -1,
            "start_work_h": -1,
            "end_work_h": -1,
            "x": -1.0,
            "y": -1.0,
        }

    def _get_default_breeding_sites_to_query(
        self, id_breeding_site: int, i: int, curr_building: int
    ) -> Dict:
        return {
            "execution_id": self._execution_id,
            "simulation_id": self._simulation_id,
            "cycle": self._cycle,
            "started_from_cycle": self._started_from_cycle,
            "name": f"BreedingSites{id_breeding_site}",
            "id": id_breeding_site,
            "date_of_birth": self._start_date,
            "active": True,
            "eggs": 0,
            "curr_building": curr_building,
            "x": -1.0,
            "y": -1.0,
        }

    def _get_default_mosquitoes_to_query(
        self, id_mosquitoes: int, i: int, state: int, id_breeding_sites: int
    ) -> Dict:
        return {
            "execution_id": self._execution_id,
            "simulation_id": self._simulation_id,
            "cycle": self._cycle,
            "started_from_cycle": self._started_from_cycle,
            "name": f"Mosquitoes{id_mosquitoes}",
            "id": id_mosquitoes,
            "date_of_birth": self._start_date,
            "speed": -1.0,
            "state": state,
            "curr_building": i,
            "bs_id": id_breeding_sites,
            "x": -1.0,
            "y": -1.0,
        }

    def create_starting_scenario(
        self,
        people_per_block: List[float],
        infected_people_per_block: List[int],
        recovered_people_per_block: List[int],
        mosquitoes_per_person: float,
        nb_breeding_sites: int,
        proportion_infected_mosquitoes_without_cases: float,
        proportion_infected_mosquitoes_with_cases: float,
        sample_size: float,
    ):
        people_records = []
        mosquitoes_records = []
        breeding_sites_records = []
        id_people = 0
        id_breeding_sites = 0
        id_mosquitoes = 0
        total_infected_mosquitoes = 0
        total_infected_people = 0

        for block, people_count in enumerate(people_per_block):
            # Aplicar sample_size aos números de pessoas
            sampled_people_count = people_count * sample_size
            sampled_infected = infected_people_per_block[block] * sample_size
            sampled_recovered = recovered_people_per_block[block] * sample_size

            health_people = max(
                0,
                sampled_people_count
                - sampled_infected
                - sampled_recovered,
            )

            for _ in range(int(health_people)):
                people_records.append(
                    self._get_default_people_to_query(id_people, block, 0)
                )
                id_people += 1

            nb_infected_people = min(sampled_infected, sampled_people_count)
            total_infected_people += nb_infected_people

            for _ in range(int(nb_infected_people)):
                people_records.append(
                    self._get_default_people_to_query(id_people, block, 1)
                )
                id_people += 1

            if nb_infected_people > 0:
                breeding_sites_records.append(
                    self._get_default_breeding_sites_to_query(
                        id_breeding_sites, block, block
                    )
                )
                id_breeding_sites += 1

            nb_mosquitoes = math.ceil(
                (health_people + nb_infected_people) * mosquitoes_per_person
            )
            proportion = (
                proportion_infected_mosquitoes_with_cases
                if nb_infected_people > 0
                else proportion_infected_mosquitoes_without_cases
            )
            nb_infected_mosquitoes = math.ceil(nb_mosquitoes * proportion)

            total_infected_mosquitoes += nb_infected_mosquitoes

            for _ in range(nb_infected_mosquitoes):
                mosquitoes_records.append(
                    self._get_default_mosquitoes_to_query(
                        id_mosquitoes,
                        block,
                        2,
                        id_breeding_sites - 1 if nb_infected_people > 0 else -1,
                    )
                )
                id_mosquitoes += 1

            for _ in range(nb_mosquitoes - nb_infected_mosquitoes):
                mosquitoes_records.append(
                    self._get_default_mosquitoes_to_query(
                        id_mosquitoes,
                        block,
                        0,
                        id_breeding_sites - 1 if nb_infected_people > 0 else -1,
                    )
                )

                id_mosquitoes += 1

        while id_breeding_sites < nb_breeding_sites:
            breeding_sites_records.append(
                self._get_default_breeding_sites_to_query(
                    id_breeding_sites, len(people_per_block) - 1, -1
                )
            )
            id_breeding_sites += 1

        logging.info(
            f"[*] Starting Size of Populations: People: {len(people_records)}, "
                f"BS: {len(breeding_sites_records)},"
                f"Mosquitoes: {len(mosquitoes_records)}, "
                f"Infected mosquitoes: {total_infected_mosquitoes}"
                f" Infected people: {total_infected_people}"
        )
        logging.info("[*] Executing queries...")

        self._connection.run_query_with_records(PEOPLE_INSERT_QUERY, people_records)
        self._connection.run_query_with_records(
            MOSQUITOES_INSERT_QUERY, mosquitoes_records
        )
        self._connection.run_query_with_records(
            BREEDING_SITES_INSERT_QUERY, breeding_sites_records
        )

        self._connection.close_all_idle_connections()
