from typing import List
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class PostgreSQLAdapter:
    def __init__(
        self,
        host="localhost",
        port=5432,
        dbname="dengue-propagation",
        user="postgres",
        password="07021997"
    ):
        self.database_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
        self.engine: Engine = create_engine(self.database_url)
        self.conn = self.engine.connect()

    def close(self):
        self.conn.close()
        self.engine.dispose()

    def close_all_idle_connections(self):
        query = text("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE pid <> pg_backend_pid()
              AND datname = :dbname
              AND state = 'idle';
        """)
        self.conn.execute(query, {"dbname": "dengue-propagation"})
        self.conn.commit()

    def drop_table(self, table_name: str):
        query = text(f"DROP TABLE IF EXISTS {table_name}")
        self.conn.execute(query)
        self.conn.commit()

    def get_notifications_between_dates(self, start_date: str, end_date: str, city: str) -> pd.DataFrame:
        print("Querying between:", start_date, "--", end_date)
        query = text("""
            SELECT * FROM cases
            WHERE city = :city
              AND data_notification BETWEEN :start_date AND :end_date
        """)
        df = pd.read_sql_query(query, self.conn, params={"city": city, "start_date": start_date, "end_date": end_date})
        return df

    def query(self, query_str: str) -> pd.DataFrame:
        query = text(query_str)
        df = pd.read_sql_query(query, self.conn)
        return df

    def clear_database(self):
        for table in ["people", "mosquitoes", "breeding_sites", "eggs", "metrics"]:
            query = text(f"DELETE FROM {table}")
            self.conn.execute(query)
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
        people_records = []
        mosquitoes_records = []
        breeding_sites_records = []

        id_people = 0
        id_breeding_sites = 0
        id_mosquitoes = 0

        for i, people_count in enumerate(people_per_block):
            health_people = max(0, people_count - infected_people_per_block[i] - recovered_people_per_block[i])

            for _ in range(int(health_people)):
                people_records.append({
                    "execution_id": execution_id,
                    "simulation_id": simulation_id,
                    "cycle": cycle,
                    "started_from_cycle": started_from_cycle,
                    "name": f"People{id_people}",
                    "id": id_people,
                    "date_of_birth": start_date,
                    "objective": "resting",
                    "speed": -1.0,
                    "state": 0,
                    "living_place": i,
                    "working_place": -1,
                    "start_work_h": -1,
                    "end_work_h": -1,
                    "x": -1.0,
                    "y": -1.0,
                })
                id_people += 1

            nb_infected_people = min(infected_people_per_block[i], people_count)
            for _ in range(int(nb_infected_people)):
                people_records.append({
                    "execution_id": execution_id,
                    "simulation_id": simulation_id,
                    "cycle": cycle,
                    "started_from_cycle": started_from_cycle,
                    "name": f"People{id_people}",
                    "id": id_people,
                    "date_of_birth": start_date,
                    "objective": "resting",
                    "speed": -1.0,
                    "state": 1,
                    "living_place": i,
                    "working_place": -1,
                    "start_work_h": -1,
                    "end_work_h": -1,
                    "x": -1.0,
                    "y": -1.0,
                })
                id_people += 1

            if nb_infected_people > 0:
                breeding_sites_records.append({
                    "execution_id": execution_id,
                    "simulation_id": simulation_id,
                    "cycle": cycle,
                    "started_from_cycle": started_from_cycle,
                    "name": f"BreedingSites{id_breeding_sites}",
                    "id": id_breeding_sites,
                    "date_of_birth": start_date,
                    "active": True,
                    "eggs": 0,
                    "curr_building": i,
                    "x": -1.0,
                    "y": -1.0,
                })
                id_breeding_sites += 1

            nb_mosquitoes = int(health_people * mosquitoes_per_person)
            proportion = (proportion_infected_mosquitoes_with_cases if nb_infected_people > 0
                          else proportion_infected_mosquitoes_without_cases)
            nb_infected_mosquitoes = int(nb_mosquitoes * proportion)

            for _ in range(nb_infected_mosquitoes):
                mosquitoes_records.append({
                    "execution_id": execution_id,
                    "simulation_id": simulation_id,
                    "cycle": cycle,
                    "started_from_cycle": started_from_cycle,
                    "name": f"Mosquitoes{id_mosquitoes}",
                    "id": id_mosquitoes,
                    "date_of_birth": start_date,
                    "speed": -1.0,
                    "state": 2,
                    "curr_building": i,
                    "bs_id": id_breeding_sites - 1 if nb_infected_people > 0 else -1,
                    "x": -1.0,
                    "y": -1.0,
                })
                id_mosquitoes += 1

            for _ in range(nb_mosquitoes - nb_infected_mosquitoes):
                mosquitoes_records.append({
                    "execution_id": execution_id,
                    "simulation_id": simulation_id,
                    "cycle": cycle,
                    "started_from_cycle": started_from_cycle,
                    "name": f"Mosquitoes{id_mosquitoes}",
                    "id": id_mosquitoes,
                    "date_of_birth": start_date,
                    "speed": -1.0,
                    "state": 0,
                    "curr_building": i,
                    "bs_id": id_breeding_sites - 1 if nb_infected_people > 0 else -1,
                    "x": -1.0,
                    "y": -1.0,
                })
                id_mosquitoes += 1

        while id_breeding_sites < nb_breeding_sites:
            breeding_sites_records.append({
                "execution_id": execution_id,
                "simulation_id": simulation_id,
                "cycle": cycle,
                "started_from_cycle": started_from_cycle,
                "name": f"BreedingSites{id_breeding_sites}",
                "id": id_breeding_sites,
                "date_of_birth": start_date,
                "active": True,
                "eggs": 0,
                "curr_building": -1,
                "x": -1.0,
                "y": -1.0,
            })
            id_breeding_sites += 1

        print(f"People: {id_people}, BS: {id_breeding_sites}, Mosquitoes: {id_mosquitoes}")
        print("Executing queries...")

        if people_records:
            self.conn.execute(
                text("""
                    INSERT INTO people
                    (execution_id, simulation_id, cycle, started_from_cycle, name, id, date_of_birth, objective, speed, state, living_place, working_place, start_work_h, end_work_h, x, y)
                    VALUES
                    (:execution_id, :simulation_id, :cycle, :started_from_cycle, :name, :id, :date_of_birth, :objective, :speed, :state, :living_place, :working_place, :start_work_h, :end_work_h, :x, :y)
                """),
                people_records
            )

        if mosquitoes_records:
            self.conn.execute(
                text("""
                    INSERT INTO mosquitoes
                    (execution_id, simulation_id, cycle, started_from_cycle, name, id, date_of_birth, speed, state, curr_building, bs_id, x, y)
                    VALUES
                    (:execution_id, :simulation_id, :cycle, :started_from_cycle, :name, :id, :date_of_birth, :speed, :state, :curr_building, :bs_id, :x, :y)
                """),
                mosquitoes_records
            )

        if breeding_sites_records:
            self.conn.execute(
                text("""
                    INSERT INTO breeding_sites
                    (execution_id, simulation_id, cycle, started_from_cycle, name, id, date_of_birth, active, eggs, curr_building, x, y)
                    VALUES
                    (:execution_id, :simulation_id, :cycle, :started_from_cycle, :name, :id, :date_of_birth, :active, :eggs, :curr_building, :x, :y)
                """),
                breeding_sites_records
            )

        self.conn.commit()
