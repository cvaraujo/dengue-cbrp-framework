import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

ALLOWED_EXPERIMENTS = {
    "vaccination",
    "parameters_sensibility",
    "parameters_tuning",
    "comparison_real_simulated",
}

@dataclass
class ExperimentConfig:
    experiment: str
    region: str
    map_size: int
    start_date: str = ""
    sample_size: float = 1.0
    max_cycles: int = 180
    output_folder: str = "./experiments"
    plot_language: str = "pt"
    people_per_m2: Optional[float] = None
    mosquitoes_per_person: Optional[float] = None
    nb_breeding_sites: Optional[int] = None
    proportion_infected_mosquitoes_without_cases: Optional[float] = None
    proportion_infected_mosquitoes_with_cases: Optional[float] = None

    @staticmethod
    def load_from_file(file_path: str) -> "ExperimentConfig":
        file_path = os.path.abspath(file_path)

        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)

        config = ExperimentConfig(
            experiment=str(data.get("experiment", "vaccination")).strip(),
            region=str(data.get("region", "")).strip(),
            map_size=int(data.get("map_size", 0)),
            start_date=data.get("start_date").strip(),
            sample_size=float(data.get("sample_size", 1.0)),
            max_cycles=int(data.get("max_cycles", 180)),
            output_folder=str(data.get("output_folder", "./experiments")).strip(),
            plot_language=str(data.get("plot_language", "pt")).strip().lower(),
            people_per_m2=_parse_optional_float(data.get("people_per_m2")),
            mosquitoes_per_person=_parse_optional_float(data.get("mosquitoes_per_person")),
            nb_breeding_sites=_parse_optional_int(data.get("nb_breeding_sites")),
            proportion_infected_mosquitoes_without_cases=_parse_optional_float(data.get("proportion_infected_mosquitoes_without_cases")),
            proportion_infected_mosquitoes_with_cases=_parse_optional_float(data.get("proportion_infected_mosquitoes_with_cases")),
        )

        config.validate()
        return config

    def validate(self) -> None:
        if self.experiment not in ALLOWED_EXPERIMENTS:
            raise ValueError(
                f"Invalid experiment '{self.experiment}'. Allowed values: {sorted(ALLOWED_EXPERIMENTS)}"
            )

        if not self.region:
            raise ValueError("The 'region' configuration value is required.")

        if not self.start_date:
            raise ValueError("The configuration must include one 'start_date'.")

        if self.sample_size <= 0 or self.sample_size > 1:
            raise ValueError("'sample_size' must be greater than 0 and less than or equal to 1.")

        if self.max_cycles <= 0:
            raise ValueError("'max_cycles' must be a positive integer.")

        if not self.output_folder:
            raise ValueError("The 'output_folder' configuration value is required.")

        if self.plot_language not in {"pt", "en"}:
            raise ValueError("'plot_language' must be 'pt' or 'en'.")

    def get_resolved_population_parameters(self) -> Tuple[float, float, int, float, float]:
        if (
            self.people_per_m2 is not None
            and self.mosquitoes_per_person is not None
            and self.nb_breeding_sites is not None
            and self.proportion_infected_mosquitoes_without_cases is not None
            and self.proportion_infected_mosquitoes_with_cases is not None
        ):
            return (
                self.people_per_m2,
                self.mosquitoes_per_person,
                self.nb_breeding_sites,
                self.proportion_infected_mosquitoes_without_cases,
                self.proportion_infected_mosquitoes_with_cases,
            )

        return get_populational_parameters(self.region)

    @classmethod
    def get_help_text(cls) -> str:
        return """
        Expected configuration file structure (JSON):

        experiment: string
            - Qual experimento rodar. Valores válidos:
            'parameters_sensibility', 'parameters_tuning', 'vaccination', 'comparison_real_simulated'.

        region: string
            - Nome da região no formato 'Bairro [Opcional], Cidade, Estado, País'.
            - Usado para selecionar parâmetros populacionais padrão quando valores explícitos não são fornecidos.

        map_size: integer
            - Tamanho do mapa OSM ou raio de consulta. Use 0 se a região não for carregada a partir de um raio em _get_city_info.

        start_date: string
            - Data de início da simulação no formato 'YYYY-MM-DD'.

        sample_size: float
            - Tamanho da amostra entre 0 e 1.0.
            - Ex.: 1.0 para 100% da amostra.

        max_cycles: integer
            - Quantidade de ciclos de simulação.

        output_folder: string
            - Pasta base de saída para os resultados.

        plot_language: string
            - Idioma dos títulos, legendas e eixos dos gráficos.
            - Valores válidos: 'pt' para português, 'en' para inglês.

        people_per_m2: float (opcional)
        mosquitoes_per_person: float (opcional)
        nb_breeding_sites: integer (opcional)
        proportion_infected_mosquitoes_without_cases: float (opcional)
        proportion_infected_mosquitoes_with_cases: float (opcional)
            - Quando omitidos, os valores serão inferidos a partir da região.

        Use o comando '--show-config-params' para exibir esta ajuda no console.
        """.strip()


def _parse_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_populational_parameters(region: str) -> Tuple[float, float, int, float, float]:
    if region == "Alto Santo, Ceará, Brasil":
        return 0.01, 1.0, 50, 0.05, 0.4

    if region  == "Limoeiro do Norte, Ceará, Brasil":
        return 0.004, 1.0, 500, 0.2, 0.9

    if region == "Guaratiba, Rio de Janeiro, Brasil":
        return 0.00117, 0.5, 720, 0.125, 0.5

    raise ValueError(f"Unknown region '{region}'. Cannot infer populational parameters. "
                      "Set the population parameters in the configuration file or in the get_populational_parameters function.")
