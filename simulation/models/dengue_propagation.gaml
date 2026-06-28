/**
* Name: Dengue Spread Simulation
* Author: Carlos V. D. Araújo
* Description:
* Tags: gis, shapefile, graph, skill, health, logistics
*/

model DenguePropagation

global {	
	// ----------------------------------------------------------
	// ------------------- Simulation Config --------------------
	// ----------------------------------------------------------
	map<string, string> POSTGRES <- [
		'host'::'localhost', 
		'dbtype'::'postgres', 
		'database'::'dengue-propagation', 
		'port'::'5432', 
		'user'::'emily'];
		
	// Step size
	float step <- 12 #h;
	// Start date string
	string start_date_str <- "2023-01-01";
	// Simulation start date
	date starting_date <- date(start_date_str + ", 05:00 AM", "yyyy-MM-dd, hh:mm a");	
	// Max number of cycles
	int max_cycles <- 60;
	// Scenario
	int scenario_id <- 1;
	// Map network
	graph road_network;
	// Load data from old simulation
	bool use_initial_scenario <- false;
	
	
	// Start from cycle
	int start_from_execution_id <- 1;
	int start_from_cycle <- 0;
	int start_from_scenario <- 1;
	// Batch end simulation
	bool end_simulation <- false;
	// Parameter to differ the batch execution 
	string simulation_name update: self.name;
	// Primary execution id to save
	int execution_id <- 1;
	bool run_batch <- false;
	bool save_states <- false;
	bool save_metrics <- false;
	
	// Default number of species
	int nb_people <- 10000;
	int nb_breeding_sites <- 300;
	int nb_mosquitoes <- 10000;
	int nb_infected_people <- 500;
	int nb_infected_mosquitoes <- 500;
	
	// Counter of species
	int cnt_people <- 0;
	int cnt_breeding_sites <- 0;
	int cnt_mosquitoes <- 0;
	 
	// ----------------------------------------------------------
	// ----------------------- Map data -------------------------
	// ----------------------------------------------------------
	// Filename of buildings and roads
	string default_shp_dir <- "/home/emily/Documentos/mestrado/simulation/dengue-cbrp-framework/src/includes/ALTO SANTO_700";
	string output_dir <- "/home/emily/Documentos/mestrado/simulation/dengue-cbrp-framework/experiments/";
	string node_filename <- default_shp_dir + "/nodes.shp";
	string road_filename <- default_shp_dir + "/edges.shp";
	string building_filename <- default_shp_dir + "/buildings.shp";	
	
	// Shapefile of the roads 
	file road_shapefile <- file(road_filename);
	// Shapefile of the intersections between roads
	file node_shapefile <- file(node_filename);
	// Shapefile of the buildings (blocks)
	file building_shapefile;
	
	//Shape of the environment
	geometry shape <- envelope(road_shapefile);
	
	// ----------------------------------------------------------
	// ---------------- People global parameters ----------------
	// ----------------------------------------------------------
	// Start-end work time
	int min_work_start <- 5;
	int max_work_start <- 8;
	int min_work_end <- 16;
	int max_work_end <- 19;
	
	// Speed
	float people_min_speed <- 20.0 #km / #h;
	float people_max_speed <- 60.0 #km / #h;
	
	// Recovery rate
	float people_daily_recovery_rate <- 0.146; // TODO: remove 0's
	
	// ----------------------------------------------------------
	// -------------- Mosquitoes global parameters --------------
	// ----------------------------------------------------------	
	// Speed
	float mosquitoes_min_speed <- 1.5 #km / #h;
	float mosquitoes_max_speed <- 2.5 #km / #h;
	float max_move_radius <- 100.0 #m;
	
	// Epidemiological
	float mosquitoes_daily_rate_of_bites <- 0.168;
	float mosquitoes_frac_infectious_bites <- 0.6;
	float mosquitoes_daily_latency_rate	<- 0.143;
	float mosquitoes_susceptibility_to_dengue <- 0.526;
	float mosquitoes_death_rate <- 0.01;
	float mosquitoes_oviposition_rate <- 0.02;
	float mosquitoes_move_probability <- 0.8;
	int mosquitoes_max_carrying_capacity <- 3;
	float mosquitoes_maturation_rate <- 0.1;
	float bs_eggs_to_mosquitoes <- 0.125;
	float bs_aquatic_phase_mortality_rate <- 0.066;
	
	//Wolbachia multipliers
	float w_mosquitoes_susceptibility_to_dengue <- 0.5;
	float w_mosquitoes_daily_latency_rate <- 0.8;
	float w_mosquitoes_daily_rate_of_bites <- 0.95;
	float w_mosquitoes_death_rate <- 1.2;
	float w_mosquitoes_oviposition_rate <- 0.8;
	float w_mosquitoes_maturation_rate <- 0.95;
	float w_bs_eggs_to_mosquitoes <- 0.7;

	int bs_capacity <- 500;	
	
	
	
	// ----------------------------------------------------------
	// --------------- Logistics global parameters --------------
	// ----------------------------------------------------------
	//cost benefit experiments
	int budget <- 0; 
	
   	bool vaccination_experiment <- false;
	float vaccine_efficacy <- 0.8;
	float prop_vaccinated <- 0.1;
	
	bool nebulizer_experiment <- false;
	float nebulizer_efficiency <- 0.8;
	int nb_blocks_nebulize <- 5;
	int count_mosquitoes_killed <- 0;
	
	bool bs_elimination_experiment <- false;
	int nb_blocks_bs_elimination <- 5;
	int count_sites_eliminate <- 0;
	
	bool parameters_experiment <- false;
	bool mosquitoes_experiment <- false;
	
	bool wolbachia_experiment <- true;
	float wolbachia_release_prop <- 0.3;
	int wolbachia_release_strategy <- 0; // 0 - inicio, 1 - mensal, 2 - qnd há pico
	bool release_completed <- false;
	int wolbachia_release_nb <- 10000;
	
	float simulation_seed <- 0.0;
	float elapsed_days <- 0.0;
	int weekday <- 1;
	int monthday <- 1;
	int total_infections <- 0;
	
//	int new_mosquitoes <- 0;	
//	int dead_mosquitoes <- 0;
//	list<int> new_mosquitoes_series <- list_with(max_cycles+1, 0);
//	list<int> dead_mosquitoes_series <- list_with(max_cycles+1, 0);
	int min_distance_to_oviposition <- 100;
	int count_infected_people <- 0;


	// ----------------------------------------------------------
	// -------------------- Global actions ----------------------
	// ----------------------------------------------------------
	
	reflex update_seed{
		seed <- simulation_seed;
		//write "seed inside reflex " + seed;
	}
	
	reflex reset_new_mosquitoes_count when: mosquitoes_experiment{
//		new_mosquitoes_series[cycle] <- new_mosquitoes;		
//		dead_mosquitoes_series[cycle] <- dead_mosquitoes;			
//		new_mosquitoes <- 0;
//		dead_mosquitoes <- 0;
		//write "reset mosquitoes";
	}
	
	reflex mosquito_per_road{
//		loop i  over: Buildings {
//			//write i;
//			list<Mosquitoes> mosquitos_in_build <- Mosquitoes where (each.current_building = i);
//		}
//		write "mosquito count: " + length(Mosquitoes);
//		write "egg count: " + length(Eggs);
	}
	
	reflex update_time{
		elapsed_days <- ((current_date - starting_date)/86400);				
		
		if(current_date.hour = 5 and current_date != starting_date){
			if weekday = 7 {
				// nebulizar
				weekday <- 0;
			} 
			
			if monthday = 30 {
				monthday <- 0;
			}
			
			weekday <- weekday + 1;	
			monthday <- monthday + 1;		
		}
		
		int wolbachia_mosquitoes <- Mosquitoes count(each.wolbachia);
		int savage_mosquitoes <- length(Mosquitoes) - wolbachia_mosquitoes;
		int wolbachia_eggs <- Eggs count(each.wolbachia);
		
		//write "wolbachia count: " + wolbachia_mosqutoes + ", savage count: " + savage_mosquitoes + ", wolbachia eggs count: " + wolbachia_eggs;
		
		//write "now is " + current_date;
		//write "its been " + elapsed_days + " days, today is weekday " + weekday + " and monthday " + monthday;
		//write ""+ People count ((each.state = 1) and (each.start_infected = false)) + " are infected";
		//if(cycle > 0){
		//	write "" + cycle_infected_people[cycle-1] + " were infected last cycle.";			
		//}
	}
	
	reflex release_wolbachia when: wolbachia_experiment and wolbachia_release_strategy != 0{
		if wolbachia_release_strategy = 1 {
			if monthday = 1 and current_date.hour = 5 {
				write "First day of the month. Releasing wolbachia!";
				do create_wolbachia;
			}
		} else{
			int curr_infected <- People count(each.state = 1);	
			int total_people <- length(People);
			if (curr_infected/total_people) >= 0.001 and not release_completed{
				write "There are > 0,1% infected people (outbreak starting). Releasing wolbachia.";
				do create_wolbachia;
				release_completed <- true;
			} 			
		}
	}
	
	reflex nebulize_critical_blocks when: (nebulizer_experiment and cycle = 2) {

		write "killing mosquitoes from " + nb_blocks_nebulize + " most critical blocks.";
	
		map<Buildings,int> cases_per_building <- [];

		// Conta infectados por prédio
		loop b over: Buildings {
	
			int n_cases <- length(
				People where (
					each.living_place = b and each.state = 1
				)
			);
	
			cases_per_building[b] <- n_cases;
	
			//write "" + b.id + " => " + n_cases;
		}
	
		// Ordena os prédios pelo número de casos
		list<Buildings> sorted_buildings <- 
			Buildings sort_by (-cases_per_building[each]);
	
		// Debug
		int nb_mosquitoes_now <- length(Mosquitoes); 
	
		loop i from: 0 to: min(nb_blocks_nebulize-1, length(sorted_buildings)-1) {
	
			Buildings critical_building <- sorted_buildings[i];
	
			//write "Building " + critical_building.id + 
			//	  " cases: " + cases_per_building[critical_building];
	
			ask Mosquitoes where (each.current_building = critical_building  and flip(nebulizer_efficiency)){
				count_mosquitoes_killed <- count_mosquitoes_killed + 1;
				do die;
			}
		}
	
		write "Reduced " + ((length(Mosquitoes)/nb_mosquitoes_now) - 1) * 100 + "% mosquitoes";
	}
	
	reflex eliminate_bs_critical_blocks when: (bs_elimination_experiment and cycle = 2) {

		write "eliminating bs from " + nb_blocks_bs_elimination + " most critical blocks.";
	
		map<Buildings,int> cases_per_building <- [];

		loop b over: Buildings {
	
			int n_cases <- length(
				People where (
					each.living_place = b and each.state = 1
				)
			);
	
			cases_per_building[b] <- n_cases;
		}
	
		list<Buildings> sorted_buildings <- 
			Buildings sort_by (-cases_per_building[each]);
	 
		int nb_bs_now <- length(BreedingSites); 
		int nb_mosquitoes_now <- length(Mosquitoes); 
	
		loop i from: 0 to: min(nb_blocks_bs_elimination-1, length(sorted_buildings)-1) {
	
			Buildings critical_building <- sorted_buildings[i];
	
			ask BreedingSites where (each.building_location = critical_building){
				ask Mosquitoes where (each.breeding_site = self){
					count_mosquitoes_killed <- count_mosquitoes_killed + 1;
					do die;
				}
				count_sites_eliminate <- count_sites_eliminate + 1;
				do die;
			}
			
		}
	
		write "Reduced " + ((length(BreedingSites)/nb_bs_now) - 1) * 100 + "% bs";
		write "Reduced " + ((length(Mosquitoes)/nb_mosquitoes_now) - 1) * 100 + "% mosquitoes";
	}
	
	reflex stop_simulation when: (start_from_cycle + cycle) >= max_cycles {
		ask Saver {
			do die;
		}
		
	   end_simulation <- true;
	   write "end simulation";
		do pause;
		
		//loop i from: 0 to: max_cycles {
		//	total_infections <- total_infections + cycle_infected_people[i];
		//}
		
		//write "" + total_infections + " were infected in total";
	}
	
	action create_wolbachia {
		int nb_wild_mosquitoes <- Mosquitoes count(!each.wolbachia);
		int nb_mosquitoes_wolbachia <- 0;
		
		if wolbachia_release_strategy = 0 {
			nb_mosquitoes_wolbachia <- 
				wolbachia_release_prop < 1.0 ?
				int(round((wolbachia_release_prop / (1.0 - wolbachia_release_prop)) * nb_wild_mosquitoes)) :
				nb_wild_mosquitoes;			
		} else {
			nb_mosquitoes_wolbachia <- wolbachia_release_nb;
		}
			
		loop i from: 1 to: nb_mosquitoes_wolbachia {
			create Mosquitoes {
				name <- "mosquitoes" + string(id);
				speed <- rnd(mosquitoes_min_speed, mosquitoes_max_speed) #km / #h;
				breeding_site <- one_of(BreedingSites);
				current_building <- one_of(breeding_site.buildings);
				location <- any_location_in(current_building);
				state <- 0;
				wolbachia <- true;
			}
		}
		
		write "created " + nb_mosquitoes_wolbachia + " wolbachia mosquitoes.";
		write "wild: " + (Mosquitoes count(!each.wolbachia));
		write "wolbachia: " + (Mosquitoes count(each.wolbachia));
		write "prop: " + ((Mosquitoes count(each.wolbachia)) / length(Mosquitoes));
	}
	
	action log_parameters{
		write "";
		write "==================================================";
		write "=============== SIMULATION PARAMETERS ============";
		write "==================================================";
	
		// ----------------------------------------------------------
		// Mosquitoes
		// ----------------------------------------------------------
		write "";
		write "----- MOSQUITOES PROBABILITIES -----";
	
		write "mosquitoes_daily_rate_of_bites: " + mosquitoes_daily_rate_of_bites;
		write "mosquitoes_frac_infectious_bites: " + mosquitoes_frac_infectious_bites;
		write "mosquitoes_daily_latency_rate: " + mosquitoes_daily_latency_rate;
		write "mosquitoes_susceptibility_to_dengue: " + mosquitoes_susceptibility_to_dengue;
		write "mosquitoes_death_rate: " + mosquitoes_death_rate;
		write "mosquitoes_oviposition_rate: " + mosquitoes_oviposition_rate;	
		write "mosquitoes_move_probability: " + mosquitoes_move_probability;
		write "mosquitoes_max_carrying_capacity: " + mosquitoes_max_carrying_capacity;	
		write "max_move_radius: " + max_move_radius;
		write "bs_eggs_to_mosquitoes: " + bs_eggs_to_mosquitoes;
		write "bs_aquatic_phase_mortality_rate: " + bs_aquatic_phase_mortality_rate;
		write "mosquitoes_maturation_rate: " + mosquitoes_maturation_rate;
		
		// ----------------------------------------------------------
		// Wolbachia
		// ----------------------------------------------------------
		
		if wolbachia_experiment{
			write "w_mosquitoes_daily_rate_of_bites: " + w_mosquitoes_daily_rate_of_bites*mosquitoes_daily_rate_of_bites;
			write "w_mosquitoes_daily_latency_rate: " + w_mosquitoes_daily_latency_rate*mosquitoes_daily_latency_rate;
			write "w_mosquitoes_susceptibility_to_dengue: " + w_mosquitoes_susceptibility_to_dengue*mosquitoes_susceptibility_to_dengue;
			write "w_mosquitoes_death_rate: " + w_mosquitoes_death_rate*mosquitoes_death_rate;
			write "w_mosquitoes_oviposition_rate: " + w_mosquitoes_oviposition_rate*mosquitoes_oviposition_rate;
			write "w_mosquitoes_maturation_rate: " + w_mosquitoes_maturation_rate*mosquitoes_maturation_rate;
			write "w_bs_eggs_to_mosquitoes: " + w_bs_eggs_to_mosquitoes*bs_eggs_to_mosquitoes;
			write "bs capacity: " + bs_capacity;
			write "release strategy: " + wolbachia_release_strategy;
			write "wolbachia_release_prop: " + wolbachia_release_prop;
			write "wolbachia_release_nb: " + wolbachia_release_nb;
		} 
	
		// ----------------------------------------------------------
		// Experiments
		// ----------------------------------------------------------
		write "";
		write "----- EXPERIMENT FLAGS -----";
	
		write "parameters_experiment: " + parameters_experiment;
		write "mosquitoes_experiment: " + mosquitoes_experiment;
		write "nebulizer_experiment: " + nebulizer_experiment;
		write "vaccination_experiment: " + vaccination_experiment;
		write "bs_elimination_experiment: " + bs_elimination_experiment;
		write "wolbachia_experiment: " + wolbachia_experiment;
		
		// ----------------------------------------------------------
		// Logistics
		// ----------------------------------------------------------
		write "";
		write "----- LOGISTICS PARAMETERS -----";
	
		write "vaccine_efficacy: " + vaccine_efficacy;
		write "prop_vaccinated: " + prop_vaccinated;
	
		write "nebulizer_efficiency: " + nebulizer_efficiency;
		write "nb_blocks_nebulize: " + nb_blocks_nebulize;
		
		write "nb_blocks_bs_elimination: " + nb_blocks_bs_elimination;
		write "budget: " + budget;
					
		
		write "";
		write "----- RANDOM-----";
		write "output folder: " + output_dir;
		
		write "==================================================";
		write "";
	}
	
	action create_street_blocks_and_save {
		// Create street-blocks
		// Get the number of blocks
		int num_blocks <- Roads max_of(each.block_id);
		
		
		loop i from: 0 to: num_blocks {
			write "" + i + " block out of " + num_blocks;
			
			// Get the roads and vertices of the block
			list<Roads> block_roads <- Roads where (each.block_id = i);
			list nodes <- block_roads collect([each.u, each.v]);
									
			list sequence <- [one_of(Vertices where(each.osmid = nodes[0][1]))];

			// Get the right sequence of arcs (streets) 
			bool has_change <- true;
			loop while: length(sequence) < length(nodes) and has_change {
				has_change <- false;
				loop j from: 1 to: length(nodes)-1 {
					if(one_of(Vertices where(each.osmid = nodes[j][0])).name = sequence[length(sequence)-1].name) {
						add one_of(Vertices where(each.osmid = nodes[j][1])) to: sequence;
						has_change <- true;
					}
				}
			}
			
			// Converte the sequence of vertices into points
			list<point> points <- sequence collect(
				point(each.location.x, each.location.y)
			);
	
			create Blocks {
				id <- i;
				block_polygon <- envelope(polygon(points));
				roads <- block_roads;
			}
		}
			
		list<Blocks> valid_blocks <- Blocks where(each.block_polygon.area > 0);
						
		ask valid_blocks {
			create Buildings from: [block_polygon] with: [id::id, road_streets::roads];
		}
		
		save Buildings to: building_filename attributes: ["name", "id", "location"] crs: "EPSG:4326";
	}
	
	action create_starting_scenario {
		// Creating Breeding sites	
		create BreedingSites number: nb_breeding_sites {
			building_location <- one_of(Buildings);
			location <- any_location_in(building_location);
			buildings <- [building_location] + Buildings at_distance(max_move_radius);
			new_eggs <- 0;
		}
		
		// Creating Mosquitoes
		// Infected
		create Mosquitoes number: nb_infected_mosquitoes {
			breeding_site <- one_of(BreedingSites);
			current_building <- one_of(breeding_site.buildings);
			location <- any_location_in(current_building);
			state <- 2;
		}
		
		// Susceptible
		create Mosquitoes number: nb_mosquitoes {
			breeding_site <- one_of(BreedingSites);
			current_building <- one_of(breeding_site.buildings);
			location <- any_location_in(current_building);
			state <- 0;
		}

		// Create people
		// Infected			
		create People number: nb_infected_people {
			living_place <- one_of(Buildings);
			working_place <- one_of(Buildings);
			location <- any_location_in(living_place);
			start_work <- rnd(min_work_start, max_work_start);
			end_work <- rnd(min_work_end, max_work_end);
			state <- 1;
		}
		
		// Susceptible
		create People number: nb_people {
			living_place <- one_of(Buildings);
			working_place <- one_of(Buildings);
			location <- any_location_in(living_place);
			start_work <- rnd(min_work_start, max_work_start);
			end_work <- rnd(min_work_end, max_work_end);
			state <- 0;
		}
	}
	
	action update_start_scenario {
		int n <- 0;
		
		string delete_query <- "";
		loop spc over: ["mosquitoes", "people", "breeding_sites", "eggs"] {
			delete_query <- delete_query + "delete from " + spc + " where execution_id=" + string(start_from_execution_id) +
			" and simulation_id=" + string(start_from_scenario) + " and cycle=" + string(start_from_cycle) + "; ";
		}
					
		/*write "[!] Removing Old Data from Database...";
		ask Saver {
			do executeUpdate(
				params: POSTGRES,
				updateComm: delete_query
			);
		}*/
				
		// --------------------------------- Mosquitoes ---------------------------------
		string prefix <- "(" + string(start_from_execution_id) + ", " + string(start_from_scenario) + ", " + string(start_from_cycle + cycle) + ", " + string(start_from_cycle);
				
		string query_mosquitoes <- "INSERT INTO mosquitoes(execution_id, simulation_id, cycle, 
			started_from_cycle, name, id, date_of_birth, speed, state, curr_building, bs_id, x, y) VALUES";
		
		int cnt <- 1;
		int nb <- length(Mosquitoes);
		
		write "[!] Querying mosquitoes... " + string(nb);
		ask Mosquitoes {
			query_mosquitoes <- query_mosquitoes + prefix + ", '" + self.name + "', " + string(self.id) + ", '" + string(self.date_of_birth) +
			"' , " + string(self.speed) + ", " + string(self.state) + ", " + string(self.current_building.id) +
			", " + string(self.breeding_site.id) + ", " + string(self.location.x) + ", " + string(self.location.y) + ")";			
			if cnt < nb {
				query_mosquitoes <- query_mosquitoes + ", ";
			} else {
				query_mosquitoes <- query_mosquitoes + "; ";
			}
			cnt <- cnt + 1;
		}
				
		// --------------------------------- People ---------------------------------	
		write "[!] Querying People...";
		string query_people <- "INSERT INTO people(execution_id, simulation_id, cycle, 
			started_from_cycle, name, id, date_of_birth, objective, speed, state, living_place,
			working_place, start_work_h, end_work_h, x, y) VALUES";
		
		cnt <- 1;
		nb <- length(People);
		
		ask People {
			query_people <- query_people + prefix + ", '" + string(self.name) + "', " + string(self.id) + ", '" + string(starting_date) +
				"', '" + self.objective + "', " + string(self.speed) + ", " + string(self.state) + ", " + string(self.living_place.id) +
				", " + string(self.working_place.id) + ", " + string(self.start_work) + ", " + string(self.end_work) + 
				", " + string(self.location.x) + ", " + string(self.location.y) + ")";
			
			if cnt < nb {
				query_people <- query_people + ", ";
			} else {
				query_people <- query_people + "; ";
			}
			cnt <- cnt + 1;
		}
		
		// --------------------------------- Breeding Sites ---------------------------------
		write "[!] Querying BS...";	
		string query_bs <- "INSERT INTO breeding_sites(execution_id, simulation_id, cycle, 
			started_from_cycle, name, id, date_of_birth, active, eggs, curr_building, x, y) VALUES";
	
		cnt <- 1;
		nb <- length(BreedingSites);
		
		ask BreedingSites {
			query_bs <- query_bs + prefix + ", '" + string(self.name) + "', " + string(self.id) + ", '" + string(starting_date) +
				"', " + string(self.active) + ", " + string(self.eggs) + ", " + string(self.building_location.id) +
				", " + string(self.location.x) + ", " + string(self.location.y) + ")";
			
			if cnt < nb {
				query_bs <- query_bs + ", ";
			} else {
				query_bs <- query_bs + "; ";
			}
			cnt <- cnt + 1;
		}
		
		/*write "[!] Inserting New Data into Database...";
		ask Saver {
			do executeUpdate(
				params: POSTGRES,
				updateComm: query_mosquitoes + query_people + query_bs
			);
		}*/
	}
	
	action load_starting_scenario {		
		bool fill_data <- false;
				
		ask Saver {			
			list<list> breeding_sites <- self.select(
				params: POSTGRES,
				select: "SELECT * FROM breeding_sites where (execution_id=? and simulation_id=? and cycle=?);",
				values:[start_from_execution_id, start_from_scenario, start_from_cycle]
			);
						
			nb_breeding_sites <- 0;
			loop bs over: breeding_sites[2] {
				string load_name <- bs[4];
				int load_id <- int(bs[5]);
				date load_date_birth <- date(bs[6]);
				bool load_active <- bool(bs[7]);
				int load_eggs <- int(bs[8]);
				int load_building <- int(bs[9]);
				float load_x <- float(bs[10]);
				float load_y <- float(bs[11]);
				
				nb_breeding_sites <- nb_breeding_sites + 1;
				
				if (load_x = -1 or load_y = -1 or load_building = -1) {
					fill_data <- true;
				}
																
				create BreedingSites {
					name <- load_name;
					id <- load_id;
					active <- load_active;
					eggs <- load_eggs;
					building_location <- load_building != -1 ? one_of(Buildings where (each.id = load_building)) : one_of(Buildings);
					location <- (load_x != -1.0 and load_y != -1.0) ? point(load_x, load_y) : any_location_in(building_location);
					buildings <- Buildings at_distance(max_move_radius);
				}
			}
			cnt_breeding_sites <- nb_breeding_sites;
			
			// ----------------------------------------------------------
			list<list> people <- self.select(
				params: POSTGRES,
				select: "SELECT * FROM people where (execution_id=? and simulation_id=? and cycle=?);",
				values:[start_from_execution_id, start_from_scenario, start_from_cycle]
			);
			
			nb_infected_people <- 0;
			nb_people <- 0;
			int nb_recovered_people <- 0;
			loop person over: people[2] {
				string load_name <- person[4];
				int load_id <- int(person[5]);
				string load_obj <- person[7];
				float load_speed <- float(person[8]);
				int load_state <- int(person[9]);
				int lp <- int(person[10]);
				int wp <- int(person[11]);
				int sw <- int(person[12]);
				int ew <- int(person[13]);
				float load_x <- float(person[14]);
				float load_y <- float(person[15]);
				
				if (load_x = -1 or load_y = -1 or load_speed = -1 or lp = -1 or wp = -1) {
					fill_data <- true;
				}
				
				if load_state = 1 {
					nb_infected_people <- nb_infected_people + 1;
				} else if load_state = 0 {
					nb_people <- nb_people + 1;	
				} else {
					nb_recovered_people <- nb_recovered_people + 1;
				}
				
				create People {
					name <- load_name;
					id <- load_id;
					objective <- load_obj;
					speed <- load_speed != -1 ? load_speed : rnd(people_min_speed, people_max_speed) #km / #h;
					state <- load_state;
					living_place <- lp != -1 ? one_of(Buildings where (each.id = lp)) : one_of(Buildings);
					working_place <- wp != -1 ? one_of(Buildings where (each.id = wp)) : one_of(Buildings);
					start_work <- sw != -1 ? sw : rnd(min_work_start, max_work_start);
					end_work <- ew != -1 ? ew : rnd(min_work_end, max_work_end);
					location <- (load_x != -1.0 and load_y != -1.0) ? point(load_x, load_y) : any_location_in(living_place);
					start_infected <- load_state = 1 ? true : false;
					vaccinated <- flip(prop_vaccinated);
				}
			}
			cnt_people <- nb_people + nb_infected_people + nb_recovered_people;			
			
			// ----------------------------------------------------------
			list<list> mosquitoes <- self.select(
				params: POSTGRES,
				select: "SELECT * FROM mosquitoes where (execution_id=? and simulation_id=? and cycle=?);",
				values:[start_from_execution_id, start_from_scenario, start_from_cycle]
			);
			
			nb_mosquitoes <- 0;
			nb_infected_mosquitoes <- 0;
			loop mosquito over: mosquitoes[2] {
				string load_name <- mosquito[4];
				int load_id <- int(mosquito[5]);
				date load_date_birth <- date(mosquito[6]);
				float load_speed <- float(mosquito[7]);
				int load_state <- int(mosquito[8]);
				int load_building <- int(mosquito[9]);
				int load_bs <- int(mosquito[10]);
				float load_x <- float(mosquito[11]);
				float load_y <- float(mosquito[12]);
				
				
				if (load_x = -1 or load_speed = -1.0 or load_building = -1) {
					fill_data <- true;
				}
				
				if load_id > cnt_mosquitoes {
					cnt_mosquitoes <- load_id + 1;
				}
				
				if load_state = 2 {
					nb_infected_mosquitoes <- nb_infected_mosquitoes + 1;
				} else {
					nb_mosquitoes <- nb_mosquitoes + 1;	
				}
				
				create Mosquitoes {
					name <- load_name;
					id <- load_id;
					speed <- load_speed != -1.0 ? load_speed : rnd(mosquitoes_min_speed, mosquitoes_max_speed) #km / #h;
					state <- load_state;
					current_building <- load_building != -1 ? one_of(Buildings where (each.id = load_building)) : one_of(Buildings);
					breeding_site <- load_bs != -1 ? one_of(BreedingSites where (each.id = load_bs)) : one_of(BreedingSites);
					location <- (load_x != -1.0 and load_y != -1.0) ? point(load_x, load_y) : any_location_in(current_building);
					wolbachia <- false;
				}
			}

			
			// ----------------------------------------------------------
			list<list> eggs <- self.select(
				params: POSTGRES,
				select: "SELECT * FROM eggs where (execution_id=? and simulation_id=? and cycle=?);",
				values:[start_from_execution_id, start_from_scenario, start_from_cycle]
			);
			
			loop egg over: eggs[2] {
				create Eggs {
					deposited_date <- date(egg[4]);
					breeding_site <- one_of(BreedingSites where (each.id = int(egg[5])));
					deposited_days <- float(egg[6]);
					
				}
			}
		}		
		
			
		if wolbachia_experiment and wolbachia_release_strategy = 0 {				
			do create_wolbachia;
		}
		
		int n_wolbachia <- Mosquitoes count(each.wolbachia);
		write "size people: " + length(People);
		write "size mosquitoes: " + length(Mosquitoes);
		write "size bs: " + length(BreedingSites);
		write "nb wolbachia: "+ n_wolbachia; 
		write "release prop: "+ (n_wolbachia / length(Mosquitoes)); 
		
		/*if fill_data {
			write "[!] Fill Data in Start Scenario...";	
			do update_start_scenario;
		}*/
	}

	// ----------------------------------------------------------
	// ----------------------- Init Model -----------------------
	// ----------------------------------------------------------
	init {
		seed <- simulation_seed;
		//execution_id <- rnd(1, 1e9);
		do log_parameters;
		
		// End the simulation if no map was provided
		if !file_exists(node_filename) or !file_exists(road_filename) {
			do die;
		}

		// Vertex
		create Vertices from: node_shapefile with: [osmid::string(read("osmid"))];
		
		// Load the roads
		create Roads from: road_shapefile with: [
			osmid::read("osmid"),
			id::int(read("id_key")),
			block_id::int(read("block")),
			u::read("u"),
			v::read("v")
		];
						
		// Define the network graph
		road_network <- as_driving_graph(Roads, Vertices);
		
		// Create the street blocks that turns into Buildings
		// Specie to save the others
		if !file_exists(building_filename) {
			write "[!] Create Street Blocks...";
			do create_street_blocks_and_save;			
		} else {
			write "[!] Load Street Blocks...";
			building_shapefile <- file(building_filename);
			create Buildings from: building_shapefile with: [name::read("name"), id::int(read("id")), location::read("location")];
			write "Nº de blocos :" + length(Buildings);
		}
		
		
		create Saver{}
		
		if use_initial_scenario {
			write "[!] Use Initial Scenario...";
			write "[!] Load Starting Scenario...";			
			do load_starting_scenario;
		} else {
			write "[!] Create Starting Scenario...";	
			do create_starting_scenario;
		}
		
		write "[!] Model is Loaded...";
		write "Seed: " + seed;
	
		simulation_seed <- seed;

		if vaccination_experiment{
			int nb_vaccinated <- People count (each.vaccinated);
			write "Number of vaccinated people: " + nb_vaccinated;
		}
	}
}

//Species to represent Mosquitoes Eggs
species Eggs {
	// Breeding site
	BreedingSites breeding_site;
	// Deposited day
	float deposited_days <- 0.0;
	date deposited_date <- current_date;
	bool wolbachia <- false;
	
	reflex turn_mosquito when: every(cycle) {
		float proba;
		if wolbachia and wolbachia_experiment{
			proba <- (w_bs_eggs_to_mosquitoes*bs_eggs_to_mosquitoes) * (w_mosquitoes_maturation_rate * mosquitoes_maturation_rate);
		} else {
			proba <- bs_eggs_to_mosquitoes * mosquitoes_maturation_rate;
		}
		
		if flip(proba) {
			// Create a new mosquito
			create Mosquitoes {
				breeding_site <- myself.breeding_site;
				current_building <- one_of(breeding_site.buildings);
				location <- any_location_in(current_building);
				state <- 0; 
				wolbachia <- myself.wolbachia;
			}
			breeding_site.eggs <- breeding_site.eggs - 1;
			//new_mosquitoes <- new_mosquitoes + 1;
			//write "new mosquito!";
			do die;
		}
	}
	
	reflex die when: flip(bs_aquatic_phase_mortality_rate) {
		breeding_site.eggs <- breeding_site.eggs - 1;
		do die;
	}
}

// Species to represent the Breeding Sites
species BreedingSites {
	// Id
	int id <- -1;
	// Location
	point location;
	// If the breeding ground can generate mosquitoes
	bool active <- true;
	// Number of eggs
	int eggs <- 0;
	// Building
	Buildings building_location;
	// Buildings in the risk area of this breeding site
	list<Buildings> buildings;
	// Eggs to crete the species
	int new_eggs <- 0;
	bool wolbachia_eggs <- false;
	
	init {
		// Update ID and count of species
		if id = -1 {
			id <- cnt_breeding_sites;
			cnt_breeding_sites <- cnt_breeding_sites + 1;
		}
	}
	
	reflex create_new_eggs when: (new_eggs > 0) {
		loop while: new_eggs > 0 and (eggs <= bs_capacity or not wolbachia_experiment){		
			eggs <- eggs + 1;
			create Eggs {
				breeding_site <- myself;
				wolbachia <- myself.wolbachia_eggs;
			}
			new_eggs <- new_eggs - 1;
		} 
		wolbachia_eggs <- false;			
		if eggs <= bs_capacity or not wolbachia_experiment{
			//write "Breeding site max capacity reached!";
		} 
	}
	
	aspect default {
		draw square(30) color: #blue;
	}		
}

// Species to represent the people using the skill moving
species People skills: [moving]{
	// id
	int id <- -1;
	// Objective (resting or working)
	string objective <- "resting";
	int start_work <- -1;
	int end_work <- -1;
	point location;
	Buildings living_place;
	Buildings working_place;
	point target;
	float speed <- rnd(people_min_speed, people_max_speed) #km / #h;
	// (SIR) Current state (susceptible = 0, infected = 1 or recovered = 2)
	int state <- 0;
	bool start_infected <- false;
	bool vaccinated <- false;
	
	init {
		if id = -1 {
			id <- cnt_people;
			cnt_people <- cnt_people + 1;
			vaccinated <- flip(prop_vaccinated);
		}
	}
	
	// Reflex to go working
	reflex time_to_work when: current_date.hour >= start_work and objective = "resting" {
		objective <- "working";
		target <- any_location_in(working_place);
	}
	
	// Reflex to go back to home
	reflex time_to_go_home when: current_date.hour >= end_work and objective = "working" {
		objective <- "resting";
		target <- any_location_in(living_place);
	}
	
	// Reflex to move to the target building
	reflex move when: target != nil {
		//we use the return_path facet to return the path followed
		do goto (target: target, on: Roads, recompute_path: false, return_path: false);
		
		if (location = target) {
			target <- nil;
		}	
	}
	
	// Reflex to change the state of the agent to infected
	reflex change_to_infected_state when: state = 0 {
		float proba <- 1 - (1 - mosquitoes_daily_rate_of_bites * mosquitoes_frac_infectious_bites);
		if self.vaccinated and vaccination_experiment {
			proba <- proba * (1 - vaccine_efficacy);
			//write "Person vaccinated, prob of infection: " + proba;
		}
		ask Mosquitoes at_distance(1 #m) {
			// Check the mosquitoes state
			if wolbachia and wolbachia_experiment{
				proba <- 1 - (1 - (w_mosquitoes_daily_rate_of_bites * mosquitoes_daily_rate_of_bites) * (w_mosquitoes_daily_rate_of_bites * mosquitoes_frac_infectious_bites));
			}
			
			if state = 2 and flip(proba){
				myself.state <- 1;
				//write "infected person";
				count_infected_people <- count_infected_people + 1;
			}
		}
	}
	
	// Reflex to change the state of the agent to recovered
	reflex change_to_recovered_state when: state = 1 and flip(people_daily_recovery_rate) {
		state <- 2;
		do die;
	}
	
	aspect default {
		int people_size <- 5;
		//draw string(id) color: #white;
		
		if state = 0 {
			draw circle(people_size) color: #yellow;
		} else if state = 1 {
			draw circle(people_size) color: #red;
		} else {
			draw circle(people_size) color: #green;
		}		
	}
	
	aspect infected {		
		if state = 0 {
			draw circle(5) color: #orange;
		} else if state = 1 {
			draw circle(5) color: #red;
		}
	}
	
}

// Species to represent the mosquitoes using the skill moving
species Mosquitoes skills: [moving] {
	// Id
	int id <- -1;
	// Default speed of the agent
	float speed <- rnd(mosquitoes_min_speed, mosquitoes_max_speed) #km / #h;
	// (SEI) State (susceptible = 0, exposed = 1 or infected = 2)
	int state <- 0;
	// Target
	point target;
	// Current location
	point location;
	// Start outbreak location
	BreedingSites breeding_site <- nil;
	// Current road
	Buildings current_building;
	//
	date date_of_birth <- current_date;
	bool wolbachia <- false;
	
	init {
		if id = -1 {
			id <- cnt_mosquitoes;
			name <- "mosquitoes" + string(cnt_mosquitoes);
			cnt_mosquitoes <- cnt_mosquitoes + 1;
		}
	}
	

	// Reflex to stay in current location or select a random destination
	reflex random_move	when: (target = nil) and (flip(mosquitoes_move_probability)) {
		current_building <- one_of(breeding_site.buildings);
		target <- any_location_in(current_building);
	}
	
	// Reflex to move to the target building
	reflex move when: target != nil {
		//we use the return_path facet to return the path followed
		do goto (target: target, on: Roads, recompute_path: false, return_path: false);
		
		if (location = target) {
			target <- nil;
		}	
	}
	
	// Reflex to change the state of the agent to exposed
	reflex change_to_exposed_state when: state = 0 {
		float proba;
		if wolbachia and wolbachia_experiment{
			proba <- 1 - (1 - (mosquitoes_daily_rate_of_bites * w_mosquitoes_daily_rate_of_bites) * (w_mosquitoes_susceptibility_to_dengue * mosquitoes_susceptibility_to_dengue));
		} else {			
			 proba <- 1 - (1 - mosquitoes_daily_rate_of_bites * mosquitoes_susceptibility_to_dengue);
		}
		
		ask People at_distance(1 #m) {
			// Check the people state
			if state = 1 and flip(proba){
				myself.state <- 1;
			}
		}
	}
	
	// Reflex to change the state of the agent to infected
	reflex change_to_infected_state when: state = 1 {
		float proba <- mosquitoes_daily_latency_rate;
		
		if wolbachia and wolbachia_experiment {
			proba <- proba * w_mosquitoes_daily_latency_rate;
		}
		
		if flip(proba){
			state <- 2;
		}
	}
	
	reflex die {
		float proba <- mosquitoes_death_rate;
		
		if wolbachia and wolbachia_experiment {
			proba <- proba * w_mosquitoes_death_rate;
		}
		
		if flip(proba){
			//dead_mosquitoes <- dead_mosquitoes + 1;
			do die;			
		}
	}
	
	// Reflex to generate a new offspring
	reflex oviposition{
		float proba <- mosquitoes_oviposition_rate;
		
		if wolbachia and wolbachia_experiment {
			proba <- proba * w_mosquitoes_oviposition_rate;
		}
		
		if flip(proba){
			BreedingSites potential_bs <- BreedingSites at_distance(min_distance_to_oviposition #m) closest_to(self);
			if potential_bs != nil {
				potential_bs.new_eggs <- rnd(1, mosquitoes_max_carrying_capacity);
				potential_bs.wolbachia_eggs <- wolbachia;
			}			
		}
	}
	
	aspect default {
		int mosquito_size <- 2;
		
		if wolbachia {
			draw circle(mosquito_size) color: #purple;
		} else if state = 0 {
			draw circle(mosquito_size) color: #yellow;
		} else if state = 1 {
			draw circle(mosquito_size) color: #orange;
		} else {
			draw circle(mosquito_size) color: #red;
		}

	}
	
	aspect infected {
		if state = 2 {
			draw circle(3) color: #orange;
		} 
	}
}

//Species to represent the buildings
species Buildings {
	int id <- -1;
	string name;
	point location;
	list<Roads> road_streets;
	
	aspect default {
		draw shape color: #gray;
	}
}

//Species to represent the roads
species Vertices skills: [intersection_skill] {
	string osmid;
	
	aspect default {
		draw circle(5) color: #black;
	}
}

species Roads skills: [road_skill] {
	string osmid;
	int id;
	int block_id;
	string u;
	string v;
	
	aspect default {
		draw shape color: #black;
	}
}

species Blocks {
	int id <- -1;
	geometry block_polygon;
	list<Roads> roads;
}

species Saver skills: [SQLSKILL] {
	reflex save_state_infected_people when: save_states and run_batch {		

		list<string> simulation_id <- simulation_name split_with ' ';
		scenario_id <- int(simulation_id[1]) + 1;
		
		let new_infected_people <- People count ((each.state = 1) and (each.start_infected = false));
		
		if (new_infected_people > 0) {
			string query_people <- "INSERT INTO metrics_infected_people(execution_id, simulation_id, cycle, id, event_date, living_place) VALUES";
			int cnt <- 0;
			
			write "[SAVE]-> " + string(execution_id) + " - " + string(scenario_id) + " - " + string(start_from_cycle + cycle) + " => " + string(new_infected_people);
			
			ask People {
				if self.state = 1 and self.start_infected = false {
					cnt <- cnt + 1;
					query_people <- query_people + "(" + string(execution_id) + ", " + string(scenario_id) + ", " + string(start_from_cycle + cycle) +
						", " + string(self.id) + ", '" + string(current_date) + "', " + string(self.living_place.id) + ")";
					
					if cnt < new_infected_people {
						query_people <- query_people + ", ";
					}
					self.start_infected <- true;				
				}
			}
			
			query_people <- query_people + ";";
			//write query_people; 
			
			do executeUpdate(
				params: POSTGRES,
				updateComm: query_people
			);
		}
 	}
   
   	reflex save_metrics when: !end_simulation and save_metrics {
//   		if (!self.isConnected()) {
//   			do connect(params: POSTGRES);
//   		}
   		
		if run_batch {
			list<string> simulation_id <- simulation_name split_with ' ';
			scenario_id <- int(simulation_id[1]) + 1;
		}
		
		write "[SAVE_METRICS] Saving on Execution: " + string(execution_id) + " - " + string(scenario_id) + " - " + string(cycle) + "...";
		
		int exposed   <- 0;
		int infected  <- People count ((each.state = 1) and (each.start_infected = false));
		int recovered <- 0;
		
		// WARNING: Do not use built in INSERT if the query has some DATE
		string query_metrics <- "INSERT INTO metrics(execution_id, simulation_id, cycle, 
			started_from_cycle, event_date, specie, susceptible, exposed, infected, recovered, dead) VALUES";	
		string prefix <- "(" + string(execution_id) + ", " + string(scenario_id) + ", " + string(start_from_cycle + cycle) + ", " + string(start_from_cycle);
		
		query_metrics <- query_metrics + prefix + ", '" + string(current_date) + "', '" + "people" + "', " + string(0) +
		", " + string(exposed) + ", " + string(infected) + ", " + string(recovered) + ", 0)";
			
		do executeUpdate(
			params: POSTGRES,
			updateComm: query_metrics
		);	
		
	}
	
	reflex save_mosquitoes_metrics when: save_states and mosquitoes_experiment and run_batch {
//		if run_batch {
//			list<string> simulation_id <- simulation_name split_with ' ';
//			scenario_id <- int(simulation_id[1]) + 1;
//		}
//		
//		int previous_mosquitoes <- length(Mosquitoes);
//
//		int infected_mosquitoes <- Mosquitoes count((each.state = 1) or (each.state = 2));
//		
//		string query <- "INSERT INTO metrics_mosquitoes(execution_id, simulation_id, cycle, new_mosquitoes, event_date, total_mosquitoes, infected_mosquitoes) VALUES" + 
//						"(" + string(execution_id) + ", " + string(scenario_id) + ", " + string(start_from_cycle + cycle) + "," + new_mosquitoes + 
//						",'" + string(current_date) + "'," + previous_mosquitoes + "," + infected_mosquitoes + ")";
//		
//
//		write "[SAVE MOSQUITOES]-> " + string(execution_id) + " - " + string(scenario_id) + " - " + string(start_from_cycle + cycle) + " => " + string(new_mosquitoes) + "," + previous_mosquitoes + "," + infected_mosquitoes;				
//
//		
//		do executeUpdate(
//			params: POSTGRES,
//			updateComm: query
//		);	
	}

	reflex save_parameters_results when: (cycle = max_cycles - 1) and parameters_experiment {
		list<string> simulation_id <- simulation_name split_with ' ';
		scenario_id <- int(simulation_id[1]) + 1;
		
		write "Finished simulation " + scenario_id + " with infected count: " + count_infected_people;
	    
	    save [
	    	execution_id,
	    	scenario_id,
	    	count_infected_people	        
	    ]
	    to: output_dir + "run_" + execution_id + "_"+ scenario_id + ".csv"
	    format: csv
	    header: true;
	}
	
	reflex save_budget_results when: (nebulizer_experiment or bs_elimination_experiment or vaccination_experiment) and run_batch {
		list<string> simulation_id <- simulation_name split_with ' ';
		scenario_id <- int(simulation_id[1]) + 1;
		int infected_people <- 0;
		int living_mosquitoes <- length(Mosquitoes);

		ask People {
			if self.state = 1 and self.start_infected = false {
				infected_people <- infected_people + 1;
				self.start_infected <- true;	
			}
		}
	    
	    save [
	    	execution_id,
			scenario_id,
			cycle,
			count_mosquitoes_killed,
			infected_people,
			living_mosquitoes
	    ]
	    to: output_dir + "/run_"+ budget + "_" + execution_id  + "_" + scenario_id + ".csv"
		rewrite: false
	    format: csv
	    header: true;
	}
	
	reflex save_wolbachia_results when: wolbachia_experiment and run_batch {
		list<string> simulation_id <- simulation_name split_with ' ';
		scenario_id <- int(simulation_id[1]) + 1;
		int infected_people <- 0;
		int wolbachia_mosquitoes <- Mosquitoes count(each.wolbachia);
		int savage_mosquitoes <- length(Mosquitoes) - wolbachia_mosquitoes;
		
		write "wolbachia count: " + wolbachia_mosquitoes + ", savage count: " + savage_mosquitoes;

		ask People {
			if self.state = 1 and self.start_infected = false {
				infected_people <- infected_people + 1;
				self.start_infected <- true;	
			}
		}
	    
	    save [
	    	execution_id,
			scenario_id,
			cycle,
			infected_people,
			wolbachia_mosquitoes,
			savage_mosquitoes
	    ]
	    to: output_dir + "/run_"+ execution_id  + "_" + scenario_id + ".csv"
		rewrite: false
	    format: csv
	    header: true;
	}
}


// ----------------------------------------------------------
// ---------------------- Experiments -----------------------
// ----------------------------------------------------------
experiment dengue_propagation type: gui until: (cycle >= max_cycles and end_simulation) {
	//
	parameter "Type of execution" var: run_batch category: "bool" init: false;
	parameter "Start Date" var: start_date_str category: "string" init: "2017-01-09";
	parameter "Max cycles" var: max_cycles category: "int" init: 5;
	parameter "Execution id" var: execution_id category: "int" init: 1;
	parameter "Shapefile:" var: default_shp_dir category: "string" init: "/home/emily/Documentos/mestrado/simulation/dengue-cbrp-framework/src/includes/Guaratiba_0";
	//
	parameter "Number of outbreak agents" var: nb_breeding_sites category: "int";
	parameter "Number of people agents" var: nb_people category: "int";
	parameter "Number of infected people agents" var: nb_infected_people category: "int";
	parameter "Number of mosquitoes agents" var: nb_mosquitoes category: "int";
	parameter "Number of infected mosquitoes agents" var: nb_infected_mosquitoes category: "int";
	//
	parameter "Maximum radius" var: max_move_radius category: "int" init: 100#m;
	
	parameter "Start from data" var: use_initial_scenario category: "bool" init: false;
	parameter "Execution number" var: start_from_execution_id category: "int" init: 1;
	parameter "Scenario number" var: start_from_scenario category: "int" init: 0;
	parameter "Cycle number" var: start_from_cycle category: "int" init: 0;
	parameter "Save" var: save_states category: "bool" init: false;
	//
	parameter "Mosquitoes oviposition" var: mosquitoes_oviposition_rate category: "float" init: 0.02;
	parameter "Mosquitoes death rate" var: mosquitoes_death_rate category: "float" init: 0.01;
	parameter "Mosquito daily mortality rate in aquatic phase" var:bs_aquatic_phase_mortality_rate category: "float" init: 0.066;
	parameter "Egg daily probability of turning into mosquito" var:bs_eggs_to_mosquitoes category: "float" init: 1.0;
	parameter "Simulation seed" var:simulation_seed category:"float" init:0.0;
	parameter "Mosquitoes move probability" var: mosquitoes_move_probability category: "float" init: 0.58789632;
	//WOLBACHIA
	parameter "Wolbachia mosquitoes oviposition" var: w_mosquitoes_oviposition_rate category: "float";
	parameter "Wolbachia mosquitoes death rate" var: w_mosquitoes_death_rate category: "float";
	parameter "Wolbachia mosquitoes suscep to dengue" var: w_mosquitoes_susceptibility_to_dengue category: "float";
	parameter "Wolbachia mosquitoes daily latency" var: w_mosquitoes_daily_latency_rate category: "float";
	parameter "Wolbachia mosquitoes maturation rate" var: w_mosquitoes_maturation_rate category: "float";
	parameter "Wolbachia mosquitoes daily rate of bites" var: w_mosquitoes_daily_rate_of_bites category: "float";
	parameter "Wolbachia mosquitoes daily probability of turning into mosquito" var: w_bs_eggs_to_mosquitoes category: "float";

	parameter "BS Capacity" var: bs_capacity category: "int";
	parameter "Wolbachia experiment" var: wolbachia_experiment category: "bool";
	parameter "Wolbachia release prop" var:  wolbachia_release_prop category: "float";
	parameter "Wolbachia release strategy" var:wolbachia_release_strategy category: "float";
	//	
	parameter "Nebulizer Efficiency" var: nebulizer_efficiency category: "float" init: 0.8;
	parameter "Number of blocks to nebulize" var: nb_blocks_nebulize category: "int";
	parameter "Nebulizer experiment" var: nebulizer_experiment category: "bool";
	//
	parameter "Proportion of vaccinated people" var:prop_vaccinated category:"float";
	parameter "Vaccination efficacy" var:vaccine_efficacy category:"float";
	parameter "Vaccination experiment" var: vaccination_experiment category: "bool";
	//
	parameter "Number of blocks to eliminate bs" var: nb_blocks_bs_elimination category: "int";
	parameter "Eliminate bs experiment" var: bs_elimination_experiment category: "bool";
	
	output {
		display city type: opengl {
//			species People;
//			species Mosquitoes;
//			species BreedingSites;
			species Roads;
			species Vertices;
			species Buildings transparency: 0.7;
		}
//		display Charts refresh: cycle < 60 axes: true {		
//			chart "Humans" type: series background: #white position: {0,0} style: exploded x_label: "Days" {
//				data "Infected" value: People count (each.state = 1) color: #red;
//				data "Recovered" value: People count (each.state = 2) color: #green;
//			}
//		}
//		display Charts refresh: cycle < max_cycles axes: true {		
//			chart "Mosquitoes population" type: series background: #white position: {0,0} style: exploded x_label: "Days" {
//				data "Total mosquitoes" value: length(Mosquitoes)  color: #blue;
//				data "New mosquitoes" value: new_mosquitoes_series[cycle] color: #green;
//				data "Dead mosquitoes" value: dead_mosquitoes_series[cycle] color: #red;
//			}
//		}		
	}
}

experiment long_headless_dengue_propagation type: batch keep_seed: true until: (cycle >= max_cycles or end_simulation) repeat: 50  parallel: true {
	//
	parameter "Type of execution" var: run_batch category: "bool" init: true;
	parameter "Start Date" var: start_date_str category: "string" init: "2020-05-08";
	parameter "Max cycles" var: max_cycles category: "int" init: 0;
	parameter "Execution id" var: execution_id category: "int" init: 1;
	parameter "Shapefile:" var: default_shp_dir category: "string";
	parameter "Output dir:" var: output_dir category: "string";
	//
	parameter "Number of outbreak agents" var: nb_breeding_sites category: "int";
	parameter "Number of people agents" var: nb_people category: "int";
	parameter "Number of infected people agents" var: nb_infected_people category: "int";
	parameter "Number of mosquitoes agents" var: nb_mosquitoes category: "int";
	parameter "Number of infected mosquitoes agents" var: nb_infected_mosquitoes category: "int";
	//
	parameter "Mosquitoes move probability" var: mosquitoes_move_probability category: "float" init: 0.5;
	parameter "Maximum radius" var: max_move_radius category: "int" init: 100#m;
	//
	parameter "Start from data" var: use_initial_scenario category: "bool" init: true;
	parameter "Execution number" var: start_from_execution_id category: "int" init: 1;
	parameter "Scenario number" var: start_from_scenario category: "int" init: 1;
	parameter "Cycle number" var: start_from_cycle category: "int" init: 0;
	parameter "Save" var: save_states category: "bool" init: false;
	//
	parameter "Mosquitoes oviposition" var: mosquitoes_oviposition_rate category: "float" init: 0.02;
	parameter "Mosquitoes death rate" var: mosquitoes_death_rate category: "float" init: 0.01;
	parameter "Mosquito daily mortality rate in aquatic phase" var:bs_aquatic_phase_mortality_rate category: "float" init: 0.066;
	parameter "Simulation seed" var:simulation_seed category:"float" init:0.0;
	//WOLBACHIA
	parameter "Wolbachia mosquitoes oviposition" var: w_mosquitoes_oviposition_rate category: "float";
	parameter "Wolbachia mosquitoes death rate" var: w_mosquitoes_death_rate category: "float";
	parameter "Wolbachia mosquitoes suscep to dengue" var: w_mosquitoes_susceptibility_to_dengue category: "float";
	parameter "Wolbachia mosquitoes daily latency" var: w_mosquitoes_daily_latency_rate category: "float";
	parameter "Wolbachia mosquitoes maturation rate" var: w_mosquitoes_maturation_rate category: "float";
	parameter "Wolbachia mosquitoes daily rate of bites" var: w_mosquitoes_daily_rate_of_bites category: "float";
	parameter "Wolbachia mosquitoes daily probability of turning into mosquito" var: w_bs_eggs_to_mosquitoes category: "float";
	parameter "BS Capacity" var: bs_capacity category: "int";
	parameter "Wolbachia experiment" var: wolbachia_experiment category: "bool";
	parameter "Wolbachia release prop" var:  wolbachia_release_prop category: "float";
	parameter "Wolbachia release strategy" var:wolbachia_release_strategy category: "float";
	//	
	parameter "Nebulizer Efficiency" var: nebulizer_efficiency category: "float" init: 0.8;
	parameter "Number of blocks to nebulize" var: nb_blocks_nebulize category: "int";
	parameter "Nebulizer experiment" var: nebulizer_experiment category: "bool";
	//
	parameter "Proportion of vaccinated people" var:prop_vaccinated category:"float";
	parameter "Vaccination efficacy" var:vaccine_efficacy category:"float";
	parameter "Vaccination experiment" var: vaccination_experiment category: "bool";
	//
	parameter "Number of blocks to eliminate bs" var: nb_blocks_bs_elimination category: "int";
	parameter "Eliminate bs experiment" var: bs_elimination_experiment category: "bool";
	//
	parameter "Containment budget" var: budget category: "int";
}

experiment short_headless_dengue_propagation type: batch keep_seed: true until: (cycle >= max_cycles or end_simulation) repeat: 20 {
	//
	parameter "Type of execution" var: run_batch category: "bool" init: true;
	parameter "Start Date" var: start_date_str category: "string" init: "2020-05-08";
	parameter "Max cycles" var: max_cycles category: "int" init: 0;
	parameter "Execution id" var: execution_id category: "int" init: 1;
	parameter "Shapefile:" var: default_shp_dir category: "string";
	parameter "Output dir:" var: output_dir category: "string";
	//
	parameter "Number of outbreak agents" var: nb_breeding_sites category: "int";
	parameter "Number of people agents" var: nb_people category: "int";
	parameter "Number of infected people agents" var: nb_infected_people category: "int";
	parameter "Number of mosquitoes agents" var: nb_mosquitoes category: "int";
	parameter "Number of infected mosquitoes agents" var: nb_infected_mosquitoes category: "int";
	//
	parameter "Mosquitoes move probability" var: mosquitoes_move_probability category: "float" init: 0.5;
	parameter "Maximum radius" var: max_move_radius category: "int" init: 100#m;
	//
	parameter "Start from data" var: use_initial_scenario category: "bool" init: true;
	parameter "Execution number" var: start_from_execution_id category: "int" init: 1;
	parameter "Scenario number" var: start_from_scenario category: "int" init: 1;
	parameter "Cycle number" var: start_from_cycle category: "int" init: 0;
	parameter "Save" var: save_states category: "bool" init: false;
	//
	parameter "Mosquitoes oviposition" var: mosquitoes_oviposition_rate category: "float" init: 0.02;
	parameter "Mosquitoes death rate" var: mosquitoes_death_rate category: "float" init: 0.01;
	parameter "Mosquito daily mortality rate in aquatic phase" var:bs_aquatic_phase_mortality_rate category: "float" init: 0.066;
	parameter "Simulation seed" var:simulation_seed category:"float" init:0.0;
	//WOLBACHIA
	parameter "Wolbachia mosquitoes oviposition" var: w_mosquitoes_oviposition_rate category: "float";
	parameter "Wolbachia mosquitoes death rate" var: w_mosquitoes_death_rate category: "float";
	parameter "Wolbachia mosquitoes suscep to dengue" var: w_mosquitoes_susceptibility_to_dengue category: "float";
	parameter "Wolbachia mosquitoes daily latency" var: w_mosquitoes_daily_latency_rate category: "float";
	parameter "Wolbachia mosquitoes maturation rate" var: w_mosquitoes_maturation_rate category: "float";
	parameter "Wolbachia mosquitoes daily rate of bites" var: w_mosquitoes_daily_rate_of_bites category: "float";
	parameter "Wolbachia mosquitoes daily probability of turning into mosquito" var: w_bs_eggs_to_mosquitoes category: "float";
	parameter "BS Capacity" var: bs_capacity category: "int";
	parameter "Wolbachia experiment" var: wolbachia_experiment category: "bool";
	parameter "Wolbachia release prop" var:  wolbachia_release_prop category: "float";
	parameter "Wolbachia release strategy" var:wolbachia_release_strategy category: "float";
	//	
	parameter "Nebulizer Efficiency" var: nebulizer_efficiency category: "float" init: 0.8;
	parameter "Number of blocks to nebulize" var: nb_blocks_nebulize category: "int";
	parameter "Nebulizer experiment" var: nebulizer_experiment category: "bool";
	//
	parameter "Proportion of vaccinated people" var:prop_vaccinated category:"float";
	parameter "Vaccination efficacy" var:vaccine_efficacy category:"float";
	parameter "Vaccination experiment" var: vaccination_experiment category: "bool";
	//
	parameter "Number of blocks to eliminate bs" var: nb_blocks_bs_elimination category: "int";
	parameter "Eliminate bs experiment" var: bs_elimination_experiment category: "bool";
	//
	parameter "Containment budget" var: budget category: "int";
}


experiment parameters_analysis type: batch repeat: 4 until: cycle >= max_cycles {
	//
	parameter "Type of execution" var: run_batch category: "bool" init: true;
	parameter "Start Date" var: start_date_str category: "string" init: "2020-05-08";
	parameter "Max cycles" var: max_cycles category: "int" init: 0;
	parameter "Execution id" var: execution_id category: "int" init: 1;
	parameter "Shapefile:" var: default_shp_dir category: "string";
	parameter "Output dir:" var: output_dir category: "string";
	//
	parameter "Number of outbreak agents" var: nb_breeding_sites category: "int";
	parameter "Number of people agents" var: nb_people category: "int";
	parameter "Number of infected people agents" var: nb_infected_people category: "int";
	parameter "Number of mosquitoes agents" var: nb_mosquitoes category: "int";
	parameter "Number of infected mosquitoes agents" var: nb_infected_mosquitoes category: "int";
	//
	parameter "Mosquitoes move probability" var: mosquitoes_move_probability category: "float" init: 0.5;
	parameter "Maximum radius" var: max_move_radius category: "int" init: 100#m;
	//
	parameter "Start from data" var: use_initial_scenario category: "bool" init: true;
	parameter "Execution number" var: start_from_execution_id category: "int" init: 1;
	parameter "Scenario number" var: start_from_scenario category: "int" init: 1;
	parameter "Cycle number" var: start_from_cycle category: "int" init: 0;
	parameter "Save" var: save_states category: "bool" init: false;
	//
	parameter "Mosquitoes oviposition" var: mosquitoes_oviposition_rate category: "float" init: 0.02;
	parameter "Mosquitoes death rate" var: mosquitoes_death_rate category: "float" init: 0.01;
	parameter "Mosquito daily mortality rate in aquatic phase" var:bs_aquatic_phase_mortality_rate category: "float" init: 0.066;
	parameter "Simulation seed" var:simulation_seed category:"float" init:0.0;
	//
	parameter "Parameters experiment" var: parameters_experiment category: "bool" init:true;
}