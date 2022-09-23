from adapters.xml.simulation_xml_adapter import XmlSimulationAdapter
import os, subprocess
from os import path


class Simulation:
    def __init__(
        self,
        num_people: int,
        num_infected_people: int,
        num_mosquitoes: int,
        num_infected_mosquitoes: int,
        num_outbreaks: int,
        shapefile_folder: str,
        headless_file: str,
        num_cycles: int,
        id=0,
        model="dengue_propagation.gaml",
        experiment="headless_dengue_propagation",
        scenario="endemic",
    ):
        self._id = id
        self._scenario = scenario
        self._model = model
        self._experiment = experiment
        self._headless_file = headless_file
        self._num_people = num_people
        self._num_infected_people = num_infected_people
        self._num_mosquitoes = num_mosquitoes
        self._num_infected_mosquitoes = num_infected_mosquitoes
        self._num_outbreaks = num_outbreaks
        self._shapefile_folder = shapefile_folder
        self._num_cycles = num_cycles

    def _prepare_environment(self):
        try:
            self._head = {
                "id": str(self._id),
                "final_step": self._num_cycles,
                "model": path.abspath(path.join("simulation/models", self._model)),
                "experiment": self._experiment,
            }

            self._parameters = {
                "building_filename": (
                    "STRING",
                    path.abspath(path.join(self._shapefile_folder, "nodes.shp")),
                ),
                "road_filename": (
                    "STRING",
                    path.abspath(path.join(self._shapefile_folder, "edges.shp")),
                ),
                "nb_people": ("INT", self._num_people),
                "nb_outbreaks": ("INT", self._num_outbreaks),
                "nb_infected_people": ("INT", self._num_infected_people),
                "nb_mosquitoes": ("INT", self._num_mosquitoes),
                "nb_infected_mosquitoes": ("INT", self._num_infected_mosquitoes),
                "nb_people": ("INT", self._num_people),
                "mosquitoes_csv_filename": (
                    "STRING",
                    path.abspath(
                        path.join(
                            "temp/simulation_states",
                            "mosquitoes_" + str(self._id) + ".csv",
                        )
                    ),
                ),
                "people_csv_filename": (
                    "STRING",
                    path.abspath(
                        path.join(
                            "temp/simulation_states",
                            "people_" + str(self._id) + ".csv",
                        )
                    ),
                ),
                "outbreaks_csv_filename": (
                    "STRING",
                    path.abspath(
                        path.join(
                            "temp/simulation_states",
                            "outbreaks_" + str(self._id) + ".csv",
                        )
                    ),
                ),
                "mosquitoes_csv_filename_output": (
                    "STRING",
                    path.abspath(
                        path.join(
                            "temp/simulation_states",
                            "mosquitoes_" + str(self._id + 1) + ".csv",
                        )
                    ),
                ),
                "people_csv_filename_output": (
                    "STRING",
                    path.abspath(
                        path.join(
                            "temp/simulation_states",
                            "people_" + str(self._id + 1) + ".csv",
                        )
                    ),
                ),
                "outbreaks_csv_filename_output": (
                    "STRING",
                    path.abspath(
                        path.join(
                            "temp/simulation_states",
                            "outbreaks_" + str(self._id + 1) + ".csv",
                        )
                    ),
                ),
            }

            self._headless_file = path.abspath(
                path.join(
                    "temp/simulation_states",
                    self._headless_file + ".xml",
                )
            )

            self._id += 1

            XmlSimulationAdapter.create_xml_headless_simulation(
                self._headless_file, self._head, self._parameters
            )
        except Exception as ex:
            print(ex)

    def _continuous_run(self):
        try:
            self._head["id"] = self._id

            self._parameters = {
                "building_filename": (
                    "STRING",
                    path.abspath(path.join(self._shapefile_folder, "nodes.shp")),
                ),
                "road_filename": (
                    "STRING",
                    path.abspath(path.join(self._shapefile_folder, "edges.shp")),
                ),
                "mosquitoes_csv_filename": (
                    "STRING",
                    path.abspath(
                        path.join(
                            "temp/simulation_states",
                            "mosquitoes_" + str(self._id) + ".csv",
                        )
                    ),
                ),
                "people_csv_filename": (
                    "STRING",
                    path.abspath(
                        path.join(
                            "temp/simulation_states",
                            "people_" + str(self._id) + ".csv",
                        )
                    ),
                ),
                "outbreaks_csv_filename": (
                    "STRING",
                    path.abspath(
                        path.join(
                            "temp/simulation_states",
                            "outbreaks_" + str(self._id) + ".csv",
                        )
                    ),
                ),
                "mosquitoes_csv_filename_output": (
                    "STRING",
                    path.abspath(
                        path.join(
                            "temp/simulation_states",
                            "mosquitoes_" + str(self._id + 1) + ".csv",
                        )
                    ),
                ),
                "people_csv_filename_output": (
                    "STRING",
                    path.abspath(
                        path.join(
                            "temp/simulation_states",
                            "people_" + str(self._id + 1) + ".csv",
                        )
                    ),
                ),
                "outbreaks_csv_filename_output": (
                    "STRING",
                    path.abspath(
                        path.join(
                            "temp/simulation_states",
                            "outbreaks_" + str(self._id + 1) + ".csv",
                        )
                    ),
                ),
            }

            self._id += 1

            XmlSimulationAdapter.create_xml_headless_simulation(
                self._headless_file, self._head, self._parameters
            )
        except Exception as ex:
            print(ex)

    def run(self) -> bool:
        try:
            if self._id < 1:
                self._prepare_environment()
            else:
                self._continuous_run()

            command = (
                "bash /opt/gama-1.8.2/headless/gama-headless.sh -v "
                + self._headless_file
                + " "
                + path.abspath("temp/simulation_outputs")
            )
            print(command)
            p = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            msg, _ = p.communicate()
            if msg:
                return True
        except Exception as ex:
            print(ex)
            return False
