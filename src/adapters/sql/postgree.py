from typing import List
from venv import logger
import pandas as pd
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from adapters.sql.queries import NOTIFICATIONS_BETWEEN_DATES_QUERY

logging.basicConfig(level=logging.INFO)


class PostgreSQLAdapter:
    def __init__(
        self,
        host="localhost",
        port=5432,
        dbname="dengue-propagation",
        user="postgres",
        password="07021997",
    ):
        self.database_url = (
            f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
        )
        self.engine: Engine = create_engine(self.database_url)
        self.conn = self.engine.connect()
        self.close_all_idle_connections()

    def close(self):
        self.conn.close()
        self.engine.dispose()

    def close_all_idle_connections(self):
        query = text(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE pid <> pg_backend_pid()
              AND datname = :dbname
              AND state = 'idle';
        """
        )
        self.conn.execute(query, {"dbname": "dengue-propagation"})
        self.conn.commit()

    def drop_table(self, table_name: str):
        query = text(f"DROP TABLE IF EXISTS {table_name}")
        self.conn.execute(query)
        self.conn.commit()

    def get_notifications_between_dates(
        self, start_date: str, end_date: str, city: str
    ) -> pd.DataFrame:
        logger.info(f"[*]Querying between: { start_date} and {end_date} for {city}... ")

        df = pd.read_sql_query(
            NOTIFICATIONS_BETWEEN_DATES_QUERY,
            self.conn,
            params={"city": city, "start_date": start_date, "end_date": end_date},
        )
        return df

    def query(self, query_str: str) -> pd.DataFrame:
        query = text(query_str)
        df = pd.read_sql_query(query, self.conn)
        return df

    def clear_database(self):
        for table in [
            "people",
            "mosquitoes",
            "breeding_sites",
            "eggs",
            "metrics",
            "metrics_infected_people",
        ]:
            query = text(f"DELETE FROM {table}")
            self.conn.execute(query)
        self.conn.commit()

    def run_query_with_records(self, query: str, records: List):
        if len(records) > 0:
            self.conn.execute(query, records)
            self.conn.commit()
