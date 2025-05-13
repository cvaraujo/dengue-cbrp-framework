import psycopg2
import pandas as pd
from typing import List


class PostgreSQLAdapter:
    def __init__(self, host="localhost", port=5432, dbname="dengue-propagation", user="araujo", password="admin"):
        self.conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        self.cursor = self.conn.cursor()

    def close(self):
        self.cursor.close()
        self.conn.close()

    def close_all_idle_connections(self):
        query = """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE pid <> pg_backend_pid()
              AND datname = 'dengue-propagation'
              AND state = 'idle';
        """
        self.cursor.execute(query)
        self.conn.commit()

    def drop_table(self, table_name: str):
        self.cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        self.conn.commit()

    def get_notifications_between_dates(self, start_date: str, end_date: str, city: str) -> pd.DataFrame:
        print("Querying between:", start_date, "=>", end_date)
        query = f"""
            SELECT * FROM cases
            WHERE city = '{city}' AND data_notification BETWEEN '{start_date}' AND '{end_date}'
        """
        return pd.read_sql_query(query, self.conn)

    def query(self, query: str) -> pd.DataFrame:
        return pd.read_sql_query(query, self.conn)

    def clear_database(self):
        for table in ["people", "mosquitoes", "breeding_sites", "eggs", "metrics"]:
            self.cursor.execute(f"DELETE FROM {table}")
        self.conn.commit()

    def create_starting_scenario(
        self,
        execution_id: int,
        simulation_id: int,
        cycle: int,
        started_from_cycle: int,
        start_date: str,
        people_per_block: List[float],
        infected_people_per_block: List[int],
        recovered_people_per_block: List[int],
        mosquitoes_per_person: float,
        nb_breeding_sites: int,
        proportion_infected_mosquitoes_without_cases: float,
        proportion_infected_mosquitoes_with_cases: float
    ):
        id_people = id_breeding_sites = id_mosquitoes = 0

        people_values = []
        mosquitoes_values = []
        breeding_sites_values = []

        for i, people_count in enumerate(people_per_block):
            health_people = max(0, people_count - infected_people_per_block[i] - recovered_people_per_block[i])

            for _ in range(int(health_people)):
                people_values.append(f"({execution_id}, {simulation_id}, {cycle}, {started_from_cycle}, 'People{id_people}', {id_people}, '{start_date}', 'resting', -1.0, 0, {i}, -1, -1, -1, -1.0, -1.0)")
                id_people += 1

            nb_infected_people = min(infected_people_per_block[i], people_count)
            for _ in range(int(nb_infected_people)):
                people_values.append(f"({execution_id}, {simulation_id}, {cycle}, {started_from_cycle}, 'People{id_people}', {id_people}, '{start_date}', 'resting', -1.0, 1, {i}, -1, -1, -1, -1.0, -1.0)")
                id_people += 1

            if nb_infected_people > 0:
                breeding_sites_values.append(f"({execution_id}, {simulation_id}, {cycle}, {started_from_cycle}, 'BreedingSites{id_breeding_sites}', {id_breeding_sites}, '{start_date}', 'true', 0, {i}, -1.0, -1.0)")
                id_breeding_sites += 1

            nb_mosquitoes = int(health_people * mosquitoes_per_person)
            nb_infected_mosquitoes = int(nb_mosquitoes * (
                proportion_infected_mosquitoes_with_cases if nb_infected_people > 0 else proportion_infected_mosquitoes_without_cases
            ))

            for _ in range(nb_infected_mosquitoes):
                mosquitoes_values.append(f"({execution_id}, {simulation_id}, {cycle}, {started_from_cycle}, 'Mosquitoes{id_mosquitoes}', {id_mosquitoes}, '{start_date}', -1.0, 2, {i}, {id_breeding_sites-1 if nb_infected_people > 0 else -1}, -1.0, -1.0)")
                id_mosquitoes += 1

            for _ in range(max(0, nb_mosquitoes - nb_infected_mosquitoes)):
                mosquitoes_values.append(f"({execution_id}, {simulation_id}, {cycle}, {started_from_cycle}, 'Mosquitoes{id_mosquitoes}', {id_mosquitoes}, '{start_date}', -1.0, 0, {i}, {id_breeding_sites-1 if nb_infected_people > 0 else -1}, -1.0, -1.0)")
                id_mosquitoes += 1

        while id_breeding_sites < nb_breeding_sites:
            breeding_sites_values.append(f"({execution_id}, {simulation_id}, {cycle}, {started_from_cycle}, 'BreedingSites{id_breeding_sites}', {id_breeding_sites}, '{start_date}', 'true', 0, -1, -1.0, -1.0)")
            id_breeding_sites += 1

        print(f"People: {id_people}, BS: {id_breeding_sites}, Mosquitoes: {id_mosquitoes}")
        print("Executing queries...")

        if people_values:
            self.cursor.execute(
                "INSERT INTO people(execution_id, simulation_id, cycle, started_from_cycle, name, id, date_of_birth, objective, speed, state, living_place, working_place, start_work_h, end_work_h, x, y) VALUES " +
                ",".join(people_values)
            )

        if mosquitoes_values:
            self.cursor.execute(
                "INSERT INTO mosquitoes(execution_id, simulation_id, cycle, started_from_cycle, name, id, date_of_birth, speed, state, curr_building, bs_id, x, y) VALUES " +
                ",".join(mosquitoes_values)
            )

        if breeding_sites_values:
            self.cursor.execute(
                "INSERT INTO breeding_sites(execution_id, simulation_id, cycle, started_from_cycle, name, id, date_of_birth, active, eggs, curr_building, x, y) VALUES " +
                ",".join(breeding_sites_values)
            )

        self.conn.commit()
