from simulation_metrics import SimulationMetrics

class Experiments:

    def __init__(self):
        self.output_folder: str = "../experiments/"
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
            # parameters["mosquitoes_oviposition_rate"] = ("float", oviposition_values[i])
            # parameters["execution_id"] = ("int", i)

            # quali_run_simulation(city, db, parameters, start_date, i, inital_nb_infected, img_output * experiment_name)
            pass
        
        self.simulation_metrics.plot_multiple_cases(
            None,
            None,
            None,
            output_file,
            len(oviposition_values),
            style_dict,
        )
        


