from use_cases.simulation_metrics import *

class Experiments:
    """
    Class to run experiments on the dengue propagation simulation.
    """

    def __init__(self, output_folder: str = "../experiments/", city_name: str = "Alto Santo, Ceará, Brasil", map_size: int = 700, start_date: str = "2020-07-05"):
        self.output_folder = output_folder
        self.city_name = city_name
        self.map_size = map_size
        self.start_date = start_date
        self.params = {
            "execution_id": ("int", 0),
            "nb_people": ("int", 8100),
            "nb_infected_people": ("int", 900),
            "nb_mosquitoes": ("int", 4050),
            "nb_infected_mosquitoes": ("int", 450),
            "nb_breeding_sites": ("int", 50),
            "kill_mosquitoes": ("bool", False),
            "nb_blocks_to_kill": ("int", 20),
            "mosquitoes_oviposition_rate": ("float", 0.02),
            "mosquitoes_death_rate": ("float", 0.01),
            "simulation_seed": ("float", 0.0)
        }
        self.simulation_metrics = SimulationMetrics(self.output_folder)

    def oviposition_experiment(self):
        """
        Run an oviposition experiment to evaluate the impact of different oviposition rates on dengue transmission.
        """
        output_file = self.output_folder + "mosquitoes_oviposition_rate"
        oviposition_values = [0.02, 0.04, 0.08, 0.16, 0.32]

        style_dict = [
            {"name":f"Φ = {oviposition_values[0]}", "color":"red", "dash":"solid"},
            {"name":f"Φ = {oviposition_values[1]}", "color":"green", "dash":"dash"},
            {"name":f"Φ = {oviposition_values[2]}", "color":"orange", "dash":"dot"},
            {"name":f"Φ = {oviposition_values[3]}", "color":"blue", "dash":"dashdot"},
            {"name":f"Φ = {oviposition_values[4]}", "color":"brown", "dash":"solid"}
        ]

        for i in range(len(oviposition_values)):
            self.params["mosquitoes_oviposition_rate"] = ("float", oviposition_values[i])
            self.params["execution_id"] = ("int", i)

            result = self.simulation_metrics.run_stochastic_instance_simulation(
                self.city_name,
                self.map_size,
                self.start_date,
                i,
                self.params
            )
        
        if result:
            self.simulation_metrics.plot_multiple_cases(
                self.params["nb_infected_people"],
                output_file,
                len(oviposition_values),
                style_dict,
            )
        


