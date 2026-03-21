import logging

from use_cases.simulation_metrics import *

logging.basicConfig(level=logging.INFO)

class Experiments:
    """
    Class to run experiments on the dengue propagation simulation.
    """

    def __init__(self, 
                 output_folder,
                 city_name, 
                 map_size, 
                 start_date,
                 people_per_m2, 
                 mosquitoes_per_person, 
                 nb_breeding_sites, 
                 proportion_infected_mosquitoes_without_cases, 
                 proportion_infected_mosquitoes_with_cases,
                 max_cycles):
        self.output_folder = output_folder
        self.city_name = city_name
        self.map_size = map_size
        self.start_date = start_date
        self.people_per_m2 = people_per_m2
        self.mosquitoes_per_person = mosquitoes_per_person
        self.nb_breeding_sites = nb_breeding_sites
        self.proportion_infected_mosquitoes_without_cases = proportion_infected_mosquitoes_without_cases
        self.proportion_infected_mosquitoes_with_cases = proportion_infected_mosquitoes_with_cases
        self.max_cycles = max_cycles

        self.simulation_identifier = self.city_name.split(',')[0].strip()
       
        self.simulation_metrics = SimulationMetrics(output_folder=output_folder,
                                                        city=city_name,
                                                        map_size=map_size,
                                                        start_date=start_date,
                                                        people_per_m2=people_per_m2,
                                                        mosquitoes_per_person=mosquitoes_per_person,
                                                        nb_breeding_sites=nb_breeding_sites,
                                                        proportion_infected_mosquitoes_without_cases=proportion_infected_mosquitoes_without_cases,
                                                        proportion_infected_mosquitoes_with_cases=proportion_infected_mosquitoes_with_cases)
    
    def _get_parameters_dict(self):
        return {
            "execution_id": ("int", 0),
            "kill_mosquitoes": ("bool", False),
            "nb_blocks_to_kill": ("int", 0),
            "mosquitoes_oviposition_rate": ("float", 0.02),
            "bs_aquatic_phase_mortality_rate": ("float", 0.066),
            "mosquitoes_death_rate": ("float", 0.01),
            "simulation_seed": ("float", 0.0)
        }

    def oviposition_experiment(self):
        """
        Run an oviposition experiment to evaluate the impact of different oviposition rates on dengue transmission.
        """
        logger.info("[*] Running oviposition experiment...")    

        output_file = self.output_folder + "mosquitoes_oviposition_rate_small_values_2"
        # oviposition_values = [0.02, 0.04, 0.08, 0.16, 0.32]
        oviposition_values = [0.0, 0.0001, 0.001, 0.01, 0.1, 1.0]

        style_dict = [
            {"name":f"Φ = {oviposition_values[0]}", "color":"red", "dash":":"},
            {"name":f"Φ = {oviposition_values[1]}", "color":"green", "dash":"dashed"},
            {"name":f"Φ = {oviposition_values[2]}", "color":"orange", "dash":"dotted"},
            {"name":f"Φ = {oviposition_values[3]}", "color":"blue", "dash":"dashdot"},
            {"name":f"Φ = {oviposition_values[4]}", "color":"brown", "dash":"solid"},
            {"name":f"Φ = {oviposition_values[5]}", "color":"gray", "dash":":"},
            # {"name":f"Φ = {oviposition_values[6]}", "color":"purple", "dash":"dashed"},
            # {"name":f"Φ = {oviposition_values[7]}", "color":"pink", "dash":"dotted"},
            # {"name":f"Φ = {oviposition_values[8]}", "color":"black", "dash":"dashdot"}
        ]


        logger.info("[*] Clearing data from database...")
        self.simulation_metrics.db.clear_database()

        params = self._get_parameters_dict()

        for i in range(len(oviposition_values)):
            params["mosquitoes_oviposition_rate"] = ("float", oviposition_values[i])
            params["execution_id"] = ("int", i)

            self.simulation_metrics.compare_simulated_with_real_cases(
                exec_id=i,
                clear_db=False,
                plot=False,
                additional_params=params
            )
        
        self.simulation_metrics.plot_multiple_execs(
            output_file,
            len(oviposition_values),
            range(len(oviposition_values)),
            style_dict,
        )

        self.simulation_metrics.plot_multiple_execs_mosquitoes(
            output_file,
            len(oviposition_values),
            style_dict,
        )

        logger.info("[*] Finished oviposition experiment!")    


    def aquatic_mortality_experiment(self):
        """
        Run an aquatic mortality experiment to evaluate the impact of different aquatic death rates on dengue transmission.
        """
        logger.info("[*] Running aquatic mortality experiment...")    

        output_file = self.output_folder + "bs_aquatic_phase_mortality_rate_700"
        aquatic_mortality_values = [0.03, 0.06, 0.12, 0.24, 0.48, ]

        style_dict = [
            {"name":f"δ = {aquatic_mortality_values[0]}", "color":"red", "dash":":"},
            {"name":f"δ = {aquatic_mortality_values[1]}", "color":"green", "dash":"dashed"},
            {"name":f"δ = {aquatic_mortality_values[2]}", "color":"orange", "dash":"dotted"},
            {"name":f"δ = {aquatic_mortality_values[3]}", "color":"blue", "dash":"dashdot"},
            {"name":f"δ = {aquatic_mortality_values[4]}", "color":"brown", "dash":"solid"}
        ]

        logger.info("[*] Clearing data from database...")
        self.simulation_metrics.db.clear_database()

        params = self._get_parameters_dict()

        for i in range(len(aquatic_mortality_values)):
            params["bs_aquatic_phase_mortality_rate"] = ("float", aquatic_mortality_values[i])
            params["execution_id"] = ("int", i)

            self.simulation_metrics.compare_simulated_with_real_cases(
                exec_id=i,
                clear_db=False,
                plot=False,
                additional_params=params
            )

        self.simulation_metrics.plot_multiple_execs(
            output_file,
            len(aquatic_mortality_values),
            range(len(aquatic_mortality_values)),
            style_dict,
        )

        logger.info("[*] Finished aquatic mortality experiment!")    

    
    def mosquito_death_rate_experiment(self):
        """
        Run a mosquito death rate experiment to evaluate the impact of different mosquito death rates on dengue transmission
        """
        logger.info("[*] Running death rate experiment...")    
        
        output_file = self.output_folder + "mosquitoes_death_rate"
        death_rate_values = [0.01, 0.02, 0.04, 0.08, 0.16]

        style_dict = [
            {"name":f"μ = {death_rate_values[0]}", "color":"red", "dash":":"},
            {"name":f"μ = {death_rate_values[1]}", "color":"green", "dash":"dashed"},
            {"name":f"μ = {death_rate_values[2]}", "color":"orange", "dash":"dotted"},
            {"name":f"μ = {death_rate_values[3]}", "color":"blue", "dash":"dashdot"},
            {"name":f"μ = {death_rate_values[4]}", "color":"brown", "dash":"solid"}
        ]
        
        logger.info("[*] Clearing data from database...")
        self.simulation_metrics.db.clear_database()
        
        params = self._get_parameters_dict()
        
        for i in range(len(death_rate_values)):
            params["mosquitoes_death_rate"] = ("float", death_rate_values[i])
            params["execution_id"] = ("int", i)

            self.simulation_metrics.compare_simulated_with_real_cases(
                exec_id=i,
                clear_db=False,
                plot=False,
                additional_params=params
            )

        self.simulation_metrics.plot_multiple_execs(
            output_file,
            len(death_rate_values),
            range(len(death_rate_values)),
            style_dict,
        )

        logger.info("[*] Finished death rate experiment!")    

    def vaccine_experiment(self):
        vaccine_efficacy = [0.6, 0.7, 0.8, 0.9, 1.0]
        props_vaccinated = [0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
        style_dict = [
                {"name":f"{props_vaccinated[0] * 100}% vacinados", "color":"red", "dash":":"},
                {"name":f"{props_vaccinated[1] * 100}% vacinados", "color":"green", "dash":"dashed"},
                {"name":f"{props_vaccinated[2] * 100}% vacinados", "color":"orange", "dash":"dotted"},
                {"name":f"{props_vaccinated[3] * 100}% vacinados", "color":"blue", "dash":"dashdot"},
                {"name":f"{props_vaccinated[4] * 100}% vacinados", "color":"brown", "dash":"solid"},
                {"name":f"{props_vaccinated[5] * 100}% vacinados", "color":"gray", "dash":":"},
                {"name":f"{props_vaccinated[6] * 100}% vacinados", "color":"pink", "dash":"solid"}
        ]

        # logger.info("[*] Clearing data from database...")
        # sim_metrics.db.clear_database()

        exec_id = 0

        for efficacy in vaccine_efficacy:
            for prop in props_vaccinated:
                logger.info("[*] Running vaccine experiment for efficacy {} and proportion of vaccinated people {}...".format(efficacy, prop))
                additional_params = {
                    "prop_vaccinated": ("float", prop),
                    "vaccination_mode": ("bool", True),
                    "vaccine_efficacy": ("float", efficacy)
                }

            #     logger.info("[*] Comparing simulated with real cases for date {} and proportion of vaccinated people {}...".format(start_date, prop))
            #     sim_metrics.compare_simulated_with_real_cases(exec_id=exec_id,clear_db=False, plot=False, additional_params=additional_params)

                exec_id += 1
            
            self.simulation_metrics.plot_multiple_execs(
                self.output_folder + f"vaccination_strategies_{efficacy}",
                len(props_vaccinated),
                range(exec_id - len(props_vaccinated), exec_id),
                style_dict,
                title=f"Impact of Vaccination on Dengue cases in {self.simulation_identifier} (efficacy of {efficacy*100}%)"
            )

    def run_all_params_exp(self):
        """
        Run all parameters related experiments sequentially.
        """        
        self.oviposition_experiment()
        self.aquatic_mortality_experiment()
        self.mosquito_death_rate_experiment()  