import os
from typing import List
from matplotlib import legend
import pandas as pd
from datetime import datetime
from venv import logger

from shapely import Polygon, Point
import adapters.json.json_adapter as JsonAdapter
from domain.osm import OpenStreetMap
from domain.graph import Graph
from adapters.osm.map_adapter import MapAdapter
from adapters.sql.postgree import PostgreSQLAdapter
from use_cases.simulation import Simulation
from use_cases.scenario_generation import ScenarioGeneration
import domain.utils as Utils
import numpy as np
from datetime import timedelta, datetime
import matplotlib.pyplot as plt
import matplotlib as mpl
from scipy.stats import pearsonr
from sklearn.metrics import mean_absolute_error


class SimulationMetrics:
    def __init__(self, output_folder: str):
        self.output_folder = output_folder
        self.db = PostgreSQLAdapter()

    def _get_city_info(self, city: str):
        if city == "Alto Santo, Ceará, Brasil":
            return "ALTO SANTO", "alto-santo"
        return "LIMOEIRO", "limoeiro"

    def _build_shapefile_path(self, city_key: str, map_size: int) -> str:
        path = os.path.abspath(f"./includes/{city_key}_{map_size}")
        os.makedirs(path, exist_ok=True)
        return path

    def _prepare_parameters(
        self, shp_path, exec_id, start_date, max_cycles, save_states
    ):
        return {
            "sqlite_ds": ("string", ""),
            "max_cycles": ("int", max_cycles),
            "default_shp_dir": ("string", shp_path),
            "use_initial_scenario": ("bool", True),
            "start_from_cycle": ("int", 0),
            "start_from_scenario": ("int", 0),
            "start_from_execution_id": ("int", exec_id),
            "start_date_str": ("string", start_date),
            "execution_id": ("int", exec_id),
            "save_states": ("bool", save_states),
        }

    def compare_simulated_with_real_cases(
        self,
        city: str,
        map_size: int,
        start_date: str,
        exec_id: int,
        people_per_m2: float,
        mosquitoes_per_person: float = 0.5,
        nb_breeding_sites: int = 100,
        proportion_infected_mosquitoes_without_cases: float = 0.05,
        proportion_infected_mosquitoes_with_cases: float = 0.4,
        max_cycles: int = 180,
        plot: bool = True,
    ):
        logger.info("[*] Clearing data from database...")
        self.db.clear_database()

        logger.info(f"[*] Loading OSM map: {city} ({map_size})...")
        osm = OpenStreetMap(city, map_size)
        graph: Graph = MapAdapter.convert_osm_to_graph(osm, True)

        logger.info("[*] Retrieving dengue cases...")
        city_key, city_file = self._get_city_info(city)
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
        prev_date = start_datetime - timedelta(days=7)
        cases = self.db.get_notifications_between_dates(
            prev_date.strftime("%Y-%m-%d"), start_date, city_key
        )

        logger.info("[*] Processing blocks and population data...")
        coord_blocks: List[Polygon] = Utils.all_blocks_as_polygons(graph)
        people_block: List = Utils.compute_people_per_block(
            graph, people_per_m2, coord_blocks
        )

        logger.info(f"[*] There are {sum(people_block)} people in simulation...")

        infected, recovered = Utils.get_infected_recovered_people_per_block(
            cases, graph, start_datetime, coord_blocks
        )

        print(infected)
        starting_num_infected = np.sum(infected)

        logger.info(f"[*] Starting number of infected people {starting_num_infected}")
        if starting_num_infected < 5:
            logger.error("[!] Not enough infected people to run the simulation.")
            return

        logger.info("[*] Inserting starting scenario...")
        sg: ScenarioGeneration = ScenarioGeneration(
            execution_id=exec_id,
            simulation_id=0,
            cycle=0,
            started_from_cycle=0,
            start_date=start_date,
            connection=self.db,
        )

        sg.create_starting_scenario(
            people_per_block=people_block,
            infected_people_per_block=infected,
            recovered_people_per_block=recovered,
            mosquitoes_per_person=mosquitoes_per_person,
            nb_breeding_sites=nb_breeding_sites,
            proportion_infected_mosquitoes_without_cases=proportion_infected_mosquitoes_without_cases,
            proportion_infected_mosquitoes_with_cases=proportion_infected_mosquitoes_with_cases,
        )

        logger.info("[*] Exporting SHP files...")
        shp_path = self._build_shapefile_path(city_key, map_size)
        MapAdapter.export_osm_to_shapefile(osm, graph, shp_path)

        logger.info("[*] Running initial simulation...")
        params = self._prepare_parameters(
            shp_path, exec_id, start_date, max_cycles=0, save_states=False
        )

        sim: Simulation = Simulation()
        sim.run_simulation(JsonAdapter.convert_param_2_list(params), is_batch=False)

        logger.info("[*] Running batch simulation...")
        params = self._prepare_parameters(
            shp_path, exec_id, start_date, max_cycles=max_cycles, save_states=True
        )
        sim.run_simulation(
            JsonAdapter.convert_param_2_list(params), is_batch=True, is_short=False
        )

        if plot:
            self.plot_min_max_avg_real(
                starting_num_infected,
                start_date,
                city_key,
                exec_id,
                coord_blocks,
                os.path.join(
                    self.output_folder,
                    f"{city_key}_{map_size}_{mosquitoes_per_person}_{nb_breeding_sites}_{proportion_infected_mosquitoes_without_cases}_{proportion_infected_mosquitoes_with_cases}",
                ),
            )

        # logger.info("[*] Clearing data from database and closing GAMA...")
        # self.db.clear_database()
        # sim.kill_gama_headless()

    def plot_min_max_avg_real(
        self,
        start_num_infected: int,
        start_date: str,
        city_key: str,
        exec_id: int,
        coord_blocks: list,
        filename: str,
    ):

        logger.info("[*] Extracting and Processing simulated cases...")
        # 1. Simulated cases
        df_sim = self.db.query(
            f"""
            SELECT simulation_id, event_date
            FROM metrics_infected_people
            WHERE execution_id = {exec_id}
            """
        )

        logger.info("[*] Processing simulated notifications...")
        df_sim["event_date"] = pd.to_datetime(df_sim["event_date"])
        max_sim_date = df_sim["event_date"].max()

        df_sim["week_str"] = df_sim["event_date"].apply(
            lambda d: Utils.last_day_of_week(d).strftime("%Y-%m-%d")
        )
        df_sim["simulation_id"] = df_sim["simulation_id"].astype(str)

        df_sim_grouped = (
            df_sim.groupby(["week_str", "simulation_id"])
            .size()
            .reset_index(name="infected")
        )

        logger.info("[*] Processing real notifications...")
        df_real = self.db.get_notifications_between_dates(
            start_date, max_sim_date, city_key
        )
        df_real = df_real[
            (df_real["classification"] != 5)
            & df_real.apply(
                lambda row: any(
                    poly.contains(Point(row["y"], row["x"])) for poly in coord_blocks
                ),
                axis=1,
            )
        ][["data_notification"]]

        df_real["data_notification"] = pd.to_datetime(df_real["data_notification"])
        df_real["week_str"] = df_real["data_notification"].apply(
            lambda d: Utils.last_day_of_week(d).strftime("%Y-%m-%d")
        )

        df_real_grouped = df_real.groupby("week_str").size().to_dict()

        logger.info("[*] Processing data to plot...")
        sim_weeks = sorted(df_sim_grouped["week_str"].unique())
        metrics = []

        # First week represents the start cenários + cases from StartDate (considering approximate two cycles here)
        weeks = [1]
        avg_y = [start_num_infected]
        real_y = [start_num_infected]
        sim_x = [1]
        sim_y = [start_num_infected]
        max_sim_y = [start_num_infected]
        min_sim_y = [start_num_infected]

        metrics.append(
            {
                "Date": sim_weeks[0],
                "Avg": start_num_infected,
                "Min": start_num_infected,
                "Max": start_num_infected,
                "Real": start_num_infected,
            }
        )

        for i, week in enumerate(sim_weeks[1:], start=2):
            weekly_sim = df_sim_grouped[df_sim_grouped["week_str"] == week][
                "infected"
            ].tolist()
            weekly_real = df_real_grouped.get(week, 0)

            avg = np.mean(weekly_sim)
            min_sim = np.min(weekly_sim)
            max_sim = np.max(weekly_sim)

            metrics.append(
                {
                    "Date": week,
                    "Avg": avg,
                    "Min": min_sim,
                    "Max": max_sim,
                    "Real": weekly_real,
                }
            )

            weeks.append(i)
            avg_y.append(avg)
            real_y.append(weekly_real)
            sim_x.extend([i] * len(weekly_sim))
            sim_y.extend(weekly_sim)
            max_sim_y.append(max_sim)
            min_sim_y.append(min_sim)

        logger.info("[*] Saving basic data...")
        pd.DataFrame(metrics).to_csv(filename + ".csv", sep=",", index=False)

        logger.info("[*] Saving statistics...")
        p_avg = pearsonr(avg_y, real_y)
        corr_avg, p_value_avg = p_avg
        ci_avg = p_avg.confidence_interval(confidence_level=0.95)
        p_max = pearsonr(max_sim_y, real_y)
        corr_max, p_value_max = p_max
        ci_max = p_max.confidence_interval(confidence_level=0.95)
        mae = mean_absolute_error(real_y, avg_y)
        in_endemic_chan = sum(
            [
                1
                for i in range(len(real_y))
                if real_y[i] <= max_sim_y[i] and real_y[i] >= min_sim_y[i]
            ]
        )

        # Create a DataFrame with metrics
        df_metrics = pd.DataFrame(
            {
                "Metric": [
                    "Pearson Avg",
                    "CI Avg Lower",
                    "CI Avg Upper",
                    "P-Value Avg",
                    "Pearson Max",
                    "CI Max Lower",
                    "CI Max Upper",
                    "P-Value Max",
                    "MAE",
                    "Inside Endemic Channel",
                ],
                "Value": [
                    corr_avg,
                    ci_avg.low,
                    ci_avg.high,
                    p_value_avg,
                    corr_max,
                    ci_max.low,
                    ci_max.high,
                    p_value_max,
                    mae,
                    in_endemic_chan,
                ],
            }
        )

        # Export to CSV
        df_metrics.to_csv(filename + "_quality_metrics.csv", sep=",", index=False)

        logger.info("[*] Saving figure as PDF...")
        plt.figure(figsize=(10, 6))
        plt.plot(weeks, real_y, label="Real Cases", marker="o", linestyle="-", color="#36454F")
        plt.plot(weeks, avg_y, label="Avg Simulated Cases", linestyle="--", color="#808080")
        plt.scatter(sim_x, sim_y, label="Simulated Cases", marker="x", color="#B2BEB5")

        plt.xlabel("Weeks")
        plt.ylabel("Number of Notifications")
        plt.grid(True)
        plt.xticks(weeks)
        plt.legend()  # Show the labels in the figure
        plt.tight_layout()
        plt.savefig(filename + ".pdf", format="pdf", bbox_inches="tight")
        plt.close()

        logger.info("[*] Finished.")

    def test_plot_min_max_avg_real(
        self,
        start_num_infected: int,
        start_date: str,
        city_key: str,
        exec_id: int,
        coord_blocks: list,
        filename: str,
    ):
        # Processing Simulated Cases
        logger.info("[*] Extracting and Processing simulated cases...")
        df_sim_cases = self.db.query(
            f"SELECT simulation_id, event_date FROM metrics_infected_people WHERE execution_id = {exec_id}"
        )

        max_simulated_date: str = df_sim_cases["event_date"].max()
        df_sim_cases["event_date"] = pd.to_datetime(df_sim_cases["event_date"])
        df_sim_cases["week_str"] = df_sim_cases["event_date"].apply(
            lambda d: Utils.last_day_of_week(d).strftime("%Y-%m-%d")
        )
        df_sim_cases["simulation_id"] = df_sim_cases["simulation_id"].astype(str)
        df_sim_cases = df_sim_cases.groupby(
            ["week_str", "simulation_id"], as_index=False
        ).count()
        df_sim_cases.rename(columns={"event_date": "infected"}, inplace=True)

        # Processing real cases
        df_real_cases = self.db.get_notifications_between_dates(
            start_date, max_simulated_date, city_key
        )

        df_real_cases = df_real_cases[
            (df_real_cases["classification"] != 5)
            & df_real_cases.apply(
                lambda row: any(
                    poly.contains(Point(row["y"], row["x"])) for poly in coord_blocks
                ),
                axis=1,
            )
        ][["data_notification", "classification"]]
        df_real_cases["data_notification"] = pd.to_datetime(
            df_real_cases["data_notification"]
        )

        df_real_cases["week_str"] = df_real_cases["data_notification"].apply(
            lambda d: Utils.last_day_of_week(d).strftime("%Y-%m-%d")
        )

        # Merging all dataframes
        sim_weeks = sorted(df_sim_cases["week_str"].unique())
        metrics_to_df = [
            {
                "Date": sim_weeks[0],
                "Avg": start_num_infected,
                "Min": start_num_infected,
                "Max": start_num_infected,
                "Real": start_num_infected,
            }
        ]

        weeks = [1]
        sim_x = [1]
        avg_y = [start_num_infected]
        real_y = [start_num_infected]
        sim_y = [start_num_infected]

        for i, week in enumerate(sim_weeks[1:], start=2):
            sim_cases_per_week: list = df_sim_cases[df_sim_cases["week_str"] == week][
                "infected"
            ].to_list()

            real_cases_per_week: int = df_real_cases[
                df_real_cases["week_str"] == week
            ].shape[0]

            avg: float = np.mean(sim_cases_per_week)
            min_sim_cases: int = np.min(sim_cases_per_week)
            max_sim_cases: int = np.max(sim_cases_per_week)

            metrics_to_df.append(
                {
                    "Date": week,
                    "Avg": avg,
                    "Min": min_sim_cases,
                    "Max": max_sim_cases,
                    "Real": real_cases_per_week,
                }
            )
            weeks.append(i)
            avg_y.append(avg)
            real_y.append(real_cases_per_week)
            sim_y.extend(sim_cases_per_week)
            sim_x.extend([i] * len(sim_cases_per_week))

        # Saving basic comparison information
        pd.DataFrame(metrics_to_df).to_csv(
            filename + ".csv",
            sep=";",
            index=False,
        )

        plt.plot(weeks, real_y, label="", marker="o", linestyle="-", color="#36454F")
        plt.plot(weeks, avg_y, label="", linestyle="--", color="#808080")
        plt.scatter(sim_x, sim_y, label="", marker="x", color="#B2BEB5")

        plt.xlabel("Weeks")
        plt.ylabel("Number of Notifications")
        plt.grid(True)
        plt.xticks(weeks)
        plt.tight_layout()
        plt.savefig(filename + ".pdf", format="pdf", bbox_inches="tight")
        plt.close()
