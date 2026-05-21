import argparse
import logging

from config import ExperimentConfig
from experiment_runner import ExperimentRunner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run dengue simulation experiments using a JSON configuration file."
    )
    parser.add_argument(
        "--config-file",
        default="config.json",
        help="Path to the JSON configuration file.",
    )
    parser.add_argument(
        "--show-config-params",
        action="store_true",
        help="Show all supported config parameters and exit.",
    )
    parser.add_argument(
        "--experiment",
        help="Optional override for the experiment name defined in the config file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.show_config_params:
        print(ExperimentConfig.get_help_text())
        return

    config = ExperimentConfig.load_from_file(args.config_file)

    if args.experiment:
        config.experiment = args.experiment.strip()
        config.validate()

    logger.info(f"[*] Loaded config for experiment: {config.experiment}")

    runner = ExperimentRunner(config)
    runner.run()


if __name__ == "__main__":
    main()
