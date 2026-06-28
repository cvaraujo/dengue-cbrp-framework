from bdb import effective
from math import e
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
    def __init__(self, 
                 output_folder: str,
                 city: str,
                 map_size: int,
                 start_date: str,
                 people_per_m2: float,
                 max_cycles: int = 180,
                 mosquitoes_per_person: float = 1.0,
                 nb_breeding_sites: int = 50,
                 proportion_infected_mosquitoes_without_cases: float = 0.05,
                 proportion_infected_mosquitoes_with_cases: float = 0.4,
                 sample_size: float = 1.0,
                 plot_language: str = "pt"):
    
        self.output_folder = output_folder
        self.db = PostgreSQLAdapter()
        self.city = city
        self.map_size = map_size
        self.start_date = start_date    
        self.max_cycles = max_cycles
        self.people_per_m2 = people_per_m2
        self.mosquitoes_per_person = mosquitoes_per_person
        self.nb_breeding_sites = nb_breeding_sites
        self.proportion_infected_mosquitoes_without_cases = proportion_infected_mosquitoes_without_cases
        self.proportion_infected_mosquitoes_with_cases = proportion_infected_mosquitoes_with_cases
        self.sample_size = sample_size
        self.plot_language = plot_language.lower()
        self.plot_texts = Utils.get_plot_translations(self.plot_language)
        
        self.city_key, self.load_from_radius = self._get_city_info(self.city)
        
        (self.shp_path,  
        self.coord_blocks, 
        self.people_block, 
        self.infected, 
        self.recovered, 
        self.starting_num_infected) = self._load_simulation()

    def _get_city_info(self, city: str):
        """
        Retorna a chave da cidade e se deve carregar o mapa a partir de um raio específico.
        """
        if city == "Alto Santo, Ceará, Brasil":
            return "ALTO SANTO", True
        elif city == "Limoeiro do Norte, Ceará, Brasil":
            return "LIMOEIRO", True
        elif city == "Guaratiba, Rio de Janeiro, Brasil":
            return "Guaratiba", False
        raise ValueError(f"City '{city}' not recognized in get_city_info. Please check the configuration file.")

    def _build_shapefile_path(self, city_key: str, map_size: int) -> str:
        path = os.path.abspath(f"./src/includes/{city_key}_{map_size}")
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

    def _load_simulation(self):
        logger.info(f"[*] Loading OSM map: {self.city} ({self.map_size})...")
        osm = OpenStreetMap(self.city, self.city_key, self.map_size, self.load_from_radius)
        graph: Graph = MapAdapter.convert_osm_to_graph(osm, True)

        logger.info("[*] Retrieving dengue cases...")
        start_datetime = datetime.strptime(self.start_date, "%Y-%m-%d")
        prev_date = start_datetime - timedelta(days=6)
        cases = self.db.get_notifications_between_dates(
            prev_date.strftime("%Y-%m-%d"), self.start_date, self.city_key
        )

        logger.info("[*] Processing blocks and population data...")
        coord_blocks: List[Polygon] = Utils.all_blocks_as_polygons(graph)
        people_block: List = Utils.compute_people_per_block(
            graph, self.people_per_m2, coord_blocks
        )

        logger.info(f"[*] There are {sum(people_block)} people in simulation...")

        infected, recovered = Utils.get_infected_recovered_people_per_block(
            cases, graph, start_datetime, coord_blocks
        )

        starting_num_infected = np.sum(infected)

        logger.info(f"[*] Starting number of infected people {starting_num_infected}")
        # if starting_num_infected < 5:
        #     logger.error("[!] Not enough infected people to run the simulation.")
        #     return 0, None, None, None, None, None

        logger.info("[*] Exporting SHP files...")
        shp_path = self._build_shapefile_path(self.city_key, self.map_size)
        MapAdapter.export_osm_to_shapefile(osm, graph, shp_path)

        return shp_path, coord_blocks, people_block, infected, recovered, starting_num_infected
    
    def compare_simulated_with_real_cases(self, 
                                          exec_id: int, 
                                          clear_db: bool = True, 
                                          plot: bool = True, 
                                          additional_params: dict = None,
                                          save_states: bool = True, 
                                          experiment: str = "long_headless_dengue_propagation"):            
        if clear_db:
            logger.info("[*] Clearing data from database...")
            self.db.clear_database()

        logger.info("[*] Inserting starting scenario...")
        sg: ScenarioGeneration = ScenarioGeneration(
            execution_id=exec_id,
            simulation_id=0,
            cycle=0,
            started_from_cycle=0,
            start_date=self.start_date,
            connection=self.db,
        )

        sg.create_starting_scenario(
            people_per_block=self.people_block,
            infected_people_per_block=self.infected,
            recovered_people_per_block=self.recovered,
            mosquitoes_per_person=self.mosquitoes_per_person,
            nb_breeding_sites=self.nb_breeding_sites,
            proportion_infected_mosquitoes_without_cases=self.proportion_infected_mosquitoes_without_cases,
            proportion_infected_mosquitoes_with_cases=self.proportion_infected_mosquitoes_with_cases,
            sample_size=self.sample_size,  
        )

        logger.info("[*] Running batch simulation...")
        sim: Simulation = Simulation()
        params = self._prepare_parameters(
            self.shp_path, exec_id, self.start_date, max_cycles=self.max_cycles, save_states=save_states
        )
        params.update(additional_params or {})
        
        sim.run_simulation(
            JsonAdapter.convert_param_2_list(params), is_batch=True, is_short=False, experiment=experiment
        )

        if plot: self.plot_min_max_avg_real(exec_id=exec_id)

    def plot_min_max_avg_real(self, exec_id: int):
        filename = os.path.join(
                    self.output_folder,
                    f"{self.city_key}_{self.map_size}_{self.mosquitoes_per_person}_{self.nb_breeding_sites}_{self.proportion_infected_mosquitoes_without_cases}_{self.proportion_infected_mosquitoes_with_cases}")
        
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
            self.start_date, max_sim_date, self.city_key
        )

        df_real = df_real[
            (df_real["classification"] != 5)
            & df_real.apply(
                lambda row: any(
                    poly.contains(Point(row["x"], row["y"])) for poly in self.coord_blocks
                ),
                axis=1,
            )
        ][["data_notification"]]

        print("[*] Real notifications after filtering:", len(df_real))

        df_real["data_notification"] = pd.to_datetime(df_real["data_notification"])
        df_real["week_str"] = df_real["data_notification"].apply(
            lambda d: Utils.last_day_of_week(d).strftime("%Y-%m-%d")
        )

        df_real_grouped = df_real.groupby("week_str").size().to_dict()

        logger.info("[*] Processing data to plot...")
        sim_weeks = sorted(df_sim_grouped["week_str"].unique())
        metrics = []

        # First week represents the start cenários + cases from StartDate (considering approximate two cycles here)
        sampled_start_infected = int(round(self.starting_num_infected * self.sample_size))
        weeks = [1]
        avg_y = [sampled_start_infected]
        real_y = [sampled_start_infected]
        sim_x = [1]
        sim_y = [sampled_start_infected]
        max_sim_y = [sampled_start_infected]
        min_sim_y = [sampled_start_infected]

        metrics.append(
            {
                "Date": sim_weeks[0],
                "Avg": sampled_start_infected,
                "Min": sampled_start_infected,
                "Max": sampled_start_infected,
                "Real": sampled_start_infected,
            }
        )

        for i, week in enumerate(sim_weeks[1:], start=2):
            weekly_sim = df_sim_grouped[df_sim_grouped["week_str"] == week][
                "infected"
            ].tolist()
            weekly_real = df_real_grouped.get(week, 0)
            # Ajustar casos reais para a amostra usada na simulação
            weekly_real = int(round(weekly_real * self.sample_size))

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
        real_y_corrected,_ = Utils.detect_and_correct_outliers(real_y)
        logger.info(f"Real cases: {real_y}, Projected cases: {real_y_corrected}")
        
        p_avg = pearsonr(avg_y, real_y_corrected)
        corr_avg, p_value_avg = p_avg
        ci_avg = p_avg.confidence_interval(confidence_level=0.95)
        p_max = pearsonr(max_sim_y, real_y_corrected)
        corr_max, p_value_max = p_max
        ci_max = p_max.confidence_interval(confidence_level=0.95)
        mae = mean_absolute_error(real_y_corrected, avg_y)
        in_endemic_chan = sum(
            [
                1
                for i in range(len(real_y_corrected))
                if real_y_corrected[i] <= max_sim_y[i] and real_y_corrected[i] >= min_sim_y[i]
            ]
        )

        sum_avg_simulated = round(sum(avg_y))
        sum_real = sum(real_y_corrected)

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
                    "Sum Avg Simulated",
                    "Sum Real"
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
                    sum_avg_simulated,
                    sum_real
                ],
            }
        )

        # Export to CSV
        df_metrics.to_csv(filename + "_quality_metrics.csv", sep=",", index=False)

        logger.info("[*] Saving figure as PDF...")
        plt.figure(figsize=(10, 6))
        plt.plot(weeks, real_y, label=self.plot_texts["real_cases"], marker="o",  linestyle="-", color="#36454F")        
        plt.plot(weeks, real_y_corrected, label=self.plot_texts["real_cases_projected"], marker="o", linestyle="dotted", color="#F80000")        
        plt.plot(weeks, avg_y, label=self.plot_texts["avg_simulated"], linestyle="--", color="#808080")
        plt.scatter(sim_x, sim_y, label=self.plot_texts["simulated_cases"], marker="x", color="#B2BEB5")

        plt.xlabel(self.plot_texts["weeks"])
        plt.ylabel(self.plot_texts["number_of_notifications"])
        plt.title(self.plot_texts["epidemic_curve_title"].format(city=self.city_key, date=self.start_date))
        plt.grid(True)
        plt.xticks(weeks)
        plt.legend()  # Show the labels in the figure
        plt.tight_layout()
        plt.savefig(filename + ".pdf", format="pdf", bbox_inches="tight")
        plt.close()

        logger.info("[*] Finished.")

    def plot_multiple_execs(
        self,
        filename: str,
        n_execs: int,
        execs_ids: list,
        style: dict,
        title:str,
        plot_real: bool = True
    ):

        all_weeks = []
        all_avg_y = []

        df_sim_full = self.db.query(
            f"""
            SELECT event_date
            FROM metrics_infected_people
            """
        )

        df_sim_full["event_date"] = pd.to_datetime(df_sim_full["event_date"])
        max_sim_date = df_sim_full["event_date"].max()
        max_sim_date = datetime.strptime(self.start_date, "%Y-%m-%d") + timedelta(days=((self.max_cycles // 2) + 1))

        all_weeks_full = pd.date_range(
            start=self.start_date,
            end=max_sim_date,
            freq='W-SUN'  
        ).strftime("%Y-%m-%d").tolist()

        for i in execs_ids:
            logger.info(f"[*] Extracting and Processing simulated cases for execution {i}...")
    
            df_sim = self.db.query(
                f"""
                SELECT simulation_id, event_date
                FROM metrics_infected_people
                WHERE execution_id = {i}
                """
            )

            df_sim["event_date"] = pd.to_datetime(df_sim["event_date"])
            df_sim["week_str"] = df_sim["event_date"].apply(
                lambda d: Utils.last_day_of_week(d).strftime("%Y-%m-%d")
            )
            df_sim["simulation_id"] = df_sim["simulation_id"].astype(str)
            
            df_sim_grouped = (
                df_sim.groupby(["week_str", "simulation_id"])
                .size()
                .reset_index(name="infected")
            )

            idx = pd.MultiIndex.from_product(
                [all_weeks_full, df_sim_grouped["simulation_id"].unique()],
                names=["week_str", "simulation_id"]
            )

            df_sim_grouped = (
                df_sim_grouped.set_index(["week_str", "simulation_id"])
                .reindex(idx, fill_value=0)
                .reset_index()
            )

            print(df_sim_grouped)

            sim_weeks = sorted(df_sim_grouped["week_str"].unique())

            weeks = [1]
            avg_y = [self.starting_num_infected]

            for j, week in enumerate(sim_weeks[1:], start=2):
                weekly_sim = df_sim_grouped[df_sim_grouped["week_str"] == week][
                    "infected"
                ].tolist()

                avg = np.mean(weekly_sim)
                min_sim = np.min(weekly_sim)
                max_sim = np.max(weekly_sim)

                weeks.append(j)
                avg_y.append(avg)

            all_weeks.append(weeks)
            all_avg_y.append(avg_y)

        if plot_real:
            logger.info("[*] Processing real notifications to plot...")
            
            start_datetime = datetime.strptime(self.start_date, "%Y-%m-%d")
            prev_date = start_datetime - timedelta(days=6)
            df_real = self.db.get_notifications_between_dates(
                prev_date.strftime("%Y-%m-%d"), max_sim_date, self.city_key
            )
            df_real = df_real[
                (df_real["classification"] != 5)
                & df_real.apply(
                    lambda row: any(
                        poly.contains(Point(row["x"], row["y"])) for poly in self.coord_blocks
                    ),
                    axis=1,
                )
            ][["data_notification"]]


            df_real["data_notification"] = pd.to_datetime(df_real["data_notification"])
            df_real["week_str"] = df_real["data_notification"].apply(
                lambda d: Utils.last_day_of_week(d).strftime("%Y-%m-%d")
            )
            df_real_grouped = df_real.groupby("week_str").size().to_dict()
            sim_weeks = sorted(all_weeks_full)

            sampled_start_infected = int(round(self.starting_num_infected * self.sample_size))
            real_y = [sampled_start_infected]
            for i, week in enumerate(sim_weeks[1:], start=2):
                weekly_real = df_real_grouped.get(week, 0)
                real_y.append(int(round(weekly_real * self.sample_size)))

        logger.info("[*] Saving figure as PDF...")
        plt.figure(figsize=(10, 6))
        for i in range(n_execs):
            plt.plot(all_weeks[i], all_avg_y[i], label=style[i]["name"], color=style[i]["color"], linestyle=style[i]["dash"])

        if plot_real:
            plt.plot(all_weeks[0], real_y, label=self.plot_texts["real_cases"], marker="o", linestyle="-", color="#36454F")
            
        plt.title(title)
        plt.xlabel(self.plot_texts["week"])
        plt.ylabel(self.plot_texts["number_of_notifications"])
        plt.grid(True)
        plt.xticks(all_weeks[0])
        plt.tight_layout()
        plt.legend()
        plt.savefig(filename + ".pdf", format="pdf", bbox_inches="tight")
        plt.close()

        logger.info("[*] Finished.")    

    def plot_vaccination(
        self,
        filename: str,
        n_execs: int,
        execs_ids: list,
        style: dict,
        vaccine_efficacy: float
    ):

        all_weeks = []
        all_avg_y = []

        df_sim_full = self.db.query(
            f"""
            SELECT event_date
            FROM metrics_infected_people
            """
        )

        df_sim_full["event_date"] = pd.to_datetime(df_sim_full["event_date"])
        max_sim_date = df_sim_full["event_date"].max()
        max_sim_date = datetime.strptime(self.start_date, "%Y-%m-%d") + timedelta(days=((self.max_cycles // 2) + 1))

        all_weeks_full = pd.date_range(
            start=self.start_date,
            end=max_sim_date,
            freq='W-SUN'  
        ).strftime("%Y-%m-%d").tolist()

        for i in execs_ids:
            logger.info(f"[*] Extracting and Processing simulated cases for execution {i}...")
    
            df_sim = self.db.query(
                f"""
                SELECT simulation_id, event_date
                FROM metrics_infected_people
                WHERE execution_id = {i}
                """
            )

            df_sim["event_date"] = pd.to_datetime(df_sim["event_date"])
            df_sim["week_str"] = df_sim["event_date"].apply(
                lambda d: Utils.last_day_of_week(d).strftime("%Y-%m-%d")
            )
            df_sim["simulation_id"] = df_sim["simulation_id"].astype(str)
            
            df_sim_grouped = (
                df_sim.groupby(["week_str", "simulation_id"])
                .size()
                .reset_index(name="infected")
            )

            idx = pd.MultiIndex.from_product(
                [all_weeks_full, df_sim_grouped["simulation_id"].unique()],
                names=["week_str", "simulation_id"]
            )

            df_sim_grouped = (
                df_sim_grouped.set_index(["week_str", "simulation_id"])
                .reindex(idx, fill_value=0)
                .reset_index()
            )

            print(df_sim_grouped)

            sim_weeks = sorted(df_sim_grouped["week_str"].unique())

            weeks = [1]
            avg_y = [self.starting_num_infected]

            for j, week in enumerate(sim_weeks[1:], start=2):
                weekly_sim = df_sim_grouped[df_sim_grouped["week_str"] == week][
                    "infected"
                ].tolist()

                avg = np.mean(weekly_sim)
                min_sim = np.min(weekly_sim)
                max_sim = np.max(weekly_sim)

                weeks.append(j)
                avg_y.append(avg)

            if not len(avg_y) == len(all_weeks_full):
                missing_count = len(all_weeks_full) - len(avg_y)
                for _ in range(missing_count):
                    avg_y.append(0)
                    weeks.append(len(avg_y))

            all_weeks.append(weeks)
            all_avg_y.append(avg_y)

        logger.info("[*] Processing real notifications to plot...")
        
        start_datetime = datetime.strptime(self.start_date, "%Y-%m-%d")
        prev_date = start_datetime - timedelta(days=6)
        df_real = self.db.get_notifications_between_dates(
            prev_date.strftime("%Y-%m-%d"), max_sim_date, self.city_key
        )
        df_real = df_real[
            (df_real["classification"] != 5)
            & df_real.apply(
                lambda row: any(
                    poly.contains(Point(row["x"], row["y"])) for poly in self.coord_blocks
                ),
                axis=1,
            )
        ][["data_notification"]]


        df_real["data_notification"] = pd.to_datetime(df_real["data_notification"])
        df_real["week_str"] = df_real["data_notification"].apply(
            lambda d: Utils.last_day_of_week(d).strftime("%Y-%m-%d")
        )
        df_real_grouped = df_real.groupby("week_str").size().to_dict()
        sim_weeks = sorted(all_weeks_full)


        cases_column: dict = {self.plot_texts["real_cases"]: ([int(round(df_real_grouped.get(week_str, 0) * self.sample_size)) 
                                            for week_str in all_weeks_full])} 
        cases_column.update({style[i]["name"]: [] for i in range(n_execs)})

        cases_column[self.plot_texts["real_cases"]].append("")  # Placeholder para a última linha de redução acumulada

        real_sum = 0
        for i in range(n_execs):
            week_column = []
            avg_sum = 0
            print(f"{style[i]['name']}: {all_avg_y[i]}")
            
            for week_index in range(len(all_weeks_full)):
                week_column.append(week_index + 1)

                if not len(all_avg_y[i]) or not len(all_avg_y[i]) > week_index:
                    continue

                avg = all_avg_y[i][week_index]

                if week_index > 0: # Todos tem a mesma qtd de casos na 1a semana
                    avg_sum += avg
                
                    if i == 0: # Usa como base a primeira simulação (sem vacinação)
                        real_sum += avg

                cases_column[style[i]["name"]].append(int(avg))

            if not len(cases_column[style[i]["name"]]) == len(all_weeks_full):
                missing_count = len(all_weeks_full) - len(cases_column[style[i]["name"]])
                for _ in range(missing_count):
                    cases_column[style[i]["name"]].append(0)

            reduct_accum = (((real_sum - avg_sum) / real_sum) * 100) if real_sum > 0 else 100
            cases_column[style[i]["name"]].append(f"{reduct_accum:.2f}%")
        
        week_column.append(self.plot_texts["accumulated_reduction"])  

        print(cases_column)
        print(week_column)


        df_reduction = pd.DataFrame({self.plot_texts["week_column"]: week_column, **cases_column})
        df_reduction.to_csv(filename + "_reduction.csv", index=False)

        logger.info("[*] Saving figure as PDF...")
        plt.figure(figsize=(10, 6))
        for i in range(n_execs):
            plt.plot(all_weeks[i], all_avg_y[i], label=style[i]["name"], color=style[i]["color"], linestyle=style[i]["dash"])

        # plt.plot(all_weeks[0], real_y, label="Real Cases", marker="o", linestyle="-", color="#36454F")
            
        plt.title(self.plot_texts["vaccination_impact_title"].format(city=self.city_key, efficacy=vaccine_efficacy*100))
        plt.xlabel(self.plot_texts["week"])
        plt.ylabel(self.plot_texts["number_of_notifications"])
        plt.grid(True)
        plt.xticks(all_weeks[0])
        plt.tight_layout()
        plt.legend()
        plt.savefig(filename + ".pdf", format="pdf", bbox_inches="tight")
        plt.close()

        logger.info("[*] Finished.")    

    def plot_multiple_execs_mosquitoes(
        self,
        filename_prefix: str, 
        n_execs: int,
        style: dict
    ):
        metrics = ["new_mosquitoes", "total_mosquitoes", "infected_mosquitoes"]
       
        for metric in metrics:
            all_weeks = []
            all_avg_y = []

            df_sim_full = self.db.query(
                f"""
                SELECT event_date
                FROM metrics_mosquitoes
                """
            )

            df_sim_full["event_date"] = pd.to_datetime(df_sim_full["event_date"])
            max_sim_date = df_sim_full["event_date"].max()
            df_sim_full["week_str"] = df_sim_full["event_date"].apply(
                lambda d: Utils.last_day_of_week(d).strftime("%Y-%m-%d")
            )
            df_sim_full_grouped = (
                df_sim_full.groupby(["week_str"])
                .size()
                .reset_index(name="count")
            )

            all_weeks_full = df_sim_full_grouped["week_str"].unique()

            for i in range(n_execs):
                logger.info(f"[*] Extracting and processing mosquito data ({metric}) for execution {i}...")

                df_sim = self.db.query(
                    f"""
                    SELECT simulation_id, event_date, {metric}
                    FROM metrics_mosquitoes
                    WHERE execution_id = {i}
                    """
                )

                df_sim["event_date"] = pd.to_datetime(df_sim["event_date"])
                df_sim["week_str"] = df_sim["event_date"].apply(
                    lambda d: Utils.last_day_of_week(d).strftime("%Y-%m-%d")
                )
                df_sim["simulation_id"] = df_sim["simulation_id"].astype(str)

               
                if metric == "total_mosquitoes":
                    # Pega o valor do último dia da semana. No caso, de total_mosquitoes não queremos ver o acumulado.
                    df_sim_grouped = (
                        df_sim.sort_values("event_date")
                        .groupby(["week_str", "simulation_id"], as_index=False)
                        .last()[["week_str", "simulation_id", metric]]
                    )
                else:
                    # Pega a soma da semana para exibir o acumulado.
                    df_sim_grouped = (
                        df_sim.groupby(["week_str", "simulation_id"])[metric]
                        .sum()
                        .reset_index(name=metric)
                    )

               
                idx = pd.MultiIndex.from_product(
                    [all_weeks_full, df_sim_grouped["simulation_id"].unique()],
                    names=["week_str", "simulation_id"]
                )
                df_sim_grouped = (
                    df_sim_grouped.set_index(["week_str", "simulation_id"])
                    .reindex(idx, fill_value=0)
                    .reset_index()
                )

                sim_weeks = sorted(df_sim_grouped["week_str"].unique())
                weeks = [1]
                if metric == "total_mosquitoes":
                    avg_y = [self.mosquitoes_per_person * sum(self.people_block)] 
                else:
                    avg_y = [0]

                for j, week in enumerate(sim_weeks[1:], start=2):
                    weekly_values = df_sim_grouped[df_sim_grouped["week_str"] == week][metric].tolist()
                    print(weekly_values)
                    avg = np.mean(weekly_values)
                    weeks.append(j)
                    avg_y.append(avg)

                all_weeks.append(weeks)
                all_avg_y.append(avg_y)

           
            logger.info(f"[*] Saving figure ({metric}) as PDF...")

            plt.figure(figsize=(10, 6))
            for i in range(n_execs):
                plt.plot(
                    all_weeks[i],
                    all_avg_y[i],
                    label=style[i]["name"],
                    color=style[i]["color"],
                    linestyle=style[i]["dash"]
                )

            # plt.yscale("log")
            plt.xlabel(self.plot_texts["weeks"])
            plt.ylabel(self.plot_texts["mosquito_metric_ylabel"].format(metric=metric.replace('_', ' ').title()))
            plt.title(self.plot_texts["weekly_metric_title"].format(metric=metric.replace('_', ' ').title()))
            plt.grid(True)
            plt.xticks(all_weeks[0])
            plt.tight_layout()
            plt.legend()
            plt.savefig(f"{filename_prefix}_{metric}.pdf", format="pdf", bbox_inches="tight")
            plt.close()

            logger.info(f"[*] Finished plotting {metric}.")