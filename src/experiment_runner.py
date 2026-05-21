import logging
import os
from typing import Tuple

from use_cases import simulation
from use_cases.experiments import Experiments
from use_cases.simulation_metrics import SimulationMetrics
from config import ExperimentConfig

logger = logging.getLogger(__name__)


class ExperimentRunner:
    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.config.validate()
        self.parameters = self.config.get_resolved_population_parameters()
        self.simulation_identifier = self.config.region.split(',')[0].strip()

    def run(self) -> None:
        if self.config.experiment == "parameters_sensibility":
            self.run_parameters_sensibility_experiment()
        elif self.config.experiment == "vaccination":
            self.run_vaccination_experiment()
        elif self.config.experiment == "parameters_tuning":
            self.run_parameters_tuning_experiment()
        elif self.config.experiment == "comparison_real_simulated":
            self.run_comparison_real_simulated()
        else:
            raise ValueError(f"Unknown experiment: {self.config.experiment}")

    def _make_output_path(self, suffix: str) -> str:
        output_path = os.path.join(self.config.output_folder, suffix) if suffix else self.config.output_folder
        os.makedirs(output_path, exist_ok=True)
        return output_path

    def run_parameters_sensibility_experiment(self) -> None:
        start_date = self.config.start_date
        output_folder = self._make_output_path(f"{self.simulation_identifier}-{self.config.map_size}-{start_date}")

        logger.info(f"[*] Output folder: {output_folder}")

        experiments = Experiments(
            output_folder,
            self.config.region,
            self.config.map_size,
            start_date,
            *self.parameters,
            simulation_identifier=self.simulation_identifier,
            max_cycles=self.config.max_cycles,
            plot_language=self.config.plot_language,
        )

        logger.info("[*] Running parameters sensibility experiment...")
        experiments.run_all_params_exp()

    def run_vaccination_experiment(self) -> None:
        output_folder = self._make_output_path(f"vaccination/{self.simulation_identifier}-{self.config.map_size}-{self.config.start_date}")

        logger.info(f"[*] Output folder: {output_folder}")

        experiments = Experiments(
            output_folder,
            self.config.region,
            self.config.map_size,
            self.config.start_date,
            *self.parameters,
            simulation_identifier=self.simulation_identifier,
            max_cycles=self.config.max_cycles,
            plot_language=self.config.plot_language,
        )

        logger.info("[*] Running vaccination experiment...")
        experiments.vaccine_experiment()

    def run_parameters_tuning_experiment(self) -> None:
        output_folder = self._make_output_path("parameters_tuning")

        logger.info(f"[*] Output folder: {output_folder}")

        experiments = Experiments(
            output_folder,
            self.config.region,
            self.config.map_size,
            self.config.start_date,
            *self.parameters,
            simulation_identifier=self.simulation_identifier,
            max_cycles=self.config.max_cycles,
            plot_language=self.config.plot_language,
        )

        logger.info("[*] Running parameters tuning experiment...")
        experiments.parameters_tuning_experiment()

    def run_comparison_real_simulated(self) -> None:
        output_folder = self._make_output_path(
            f"{self.simulation_identifier}-{self.config.map_size}-{self.config.start_date}-{self.config.sample_size}sample"
        )
        logger.info(f"[*] Output folder: {output_folder}")

        sim_metrics = SimulationMetrics(
            output_folder=output_folder,
            region=self.config.region,
            max_cycles=self.config.max_cycles,
            map_size=self.config.map_size,
            start_date=self.config.start_date,
            people_per_m2=self.parameters[0],
            mosquitoes_per_person=self.parameters[1],
            nb_breeding_sites=self.parameters[2],
            proportion_infected_mosquitoes_without_cases=self.parameters[3],
            proportion_infected_mosquitoes_with_cases=self.parameters[4],
            sample_size=self.config.sample_size,
            plot_language=self.config.plot_language,
        )

        logger.info(f"[*] Comparing simulated with real cases for date {self.config.start_date}...")
        sim_metrics.compare_simulated_with_real_cases(exec_id=0, clear_db=True, plot=False)
        sim_metrics.plot_min_max_avg_real(exec_id=0)
