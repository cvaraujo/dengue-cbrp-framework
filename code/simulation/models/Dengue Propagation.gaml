/**
* Name: Dengue Scenario Simulation
* Author: Carlos Araújo
* Description:
* Tags: gis, shapefile, graph, skill, transport
**/

model DenguePropagation

global {
	//Shapefile of the buildings
	file building_shapefile <- file("../includes/tabuleiro/buildings-tabuleiro.shp");
	//Shapefile of the roads 
	file road_shapefile <- file("../includes/tabuleiro/roads-tabuleiro.shp");
	//Shape of the environment
	geometry shape <- envelope(road_shapefile);
	//Step value
	float step <- 12 #h;
	// CSV default data for the agents
//	csv_file mosquitoes_data <- csv_file("../includes/mosquitoes.csv", ";", true);
//	csv_file people_data <- csv_file("../includes/people.csv", ";", true);
//	csv_file outbreaks_data <- csv_file("../includes/outbreaks.csv", ";", true);
	
	//
	date start_date <- date("2022-01-01-05-00-00");
	
	// Work movimentation
	int min_work_start <- 6;
	int max_work_start <- 8;
	int min_work_end <- 16;
	int max_work_end <- 20;
	
	// People deafult speed
	float people_min_speed <- 1.0 #km / #h;
	float people_max_speed <- 5.0 #km / #h;
	
	// Mosquitoes deafult speed
	float mosquitoes_min_speed <- 1.0 #km / #h;
	float mosquitoes_max_speed <- 5.0 #km / #h;
	
	// Mosquitoes parameters
	float mosquitoes_daily_rate_of_bites <- 0.168;
	float mosquitoes_frac_infectious_bites <- 0.6;
	float mosquitoes_daily_latency_rate	<- 0.143;
	float mosquitoes_susceptibility_to_dengue <- 0.526;
	float mosquitoes_death_rate <- 0.05;
	
	// People parameters
	float poeple_daily_recovery_rate <- 0.143;
	
	// Outbreaks parameters
	float mosquitoes_oviposition_rate <- 0.2;
	float eggs_to_mosquitoes <- 0.125;
	int mosquitoes_max_carrying_capacity <- 3;
	float aquatic_phase_mortality_rate <- 0.06;
	
	init {
		//Initialization of the building using the shapefile of buildings
		create building from: building_shapefile;
				
		//Initialization of the road using the shapefile of roads
		create road from: road_shapefile;
		
		//
		create mosquitoes number: 200 {
			starting_point <- any_location_in(one_of(road));
			location <- starting_point;
			bounds <- circle(200, starting_point);
			state <- 2;
		}
		
		create people number: 100 {
			living_place <- one_of(road);
			working_place <- one_of(road);
			location <- any_location_in(living_place);
			start_work <- rnd(min_work_start, max_work_start);
			end_work <- rnd(min_work_end, max_work_end);
		}
		
		// Creation of the people agents
//		loop human over: people_data {
//			list<string> line <- string(human) split_with ',';
//			
//			create people {
//				// Mandatory informations
//				name <- line[0];
//				id <- int(line[1]);
//				objective <- line[2];
//				// Setting the default values and random if no value was reported
//				// Speed
//				speed<-line[3] = "nil" ? rnd(people_min_speed, people_max_speed) : float(line[3]);
//				// initial state
//				state<-line[4] = "nil" ? 0 : int(line[4]);
//				// Living place
//				living_place<-line[5] = "nil" ? one_of(building) : one_of(building where (each.osmid = line[5]));
//				// Working place
//				working_place<-line[6] = "nil" ? one_of(building) : one_of(building where (each.osmid = line[6]));
//				// Set work hours
//				start_work <- line[7] = "nil" ? rnd(min_work_start, max_work_start) : int(line[7]);
//				end_work <- line[8] = "nil" ? rnd(min_work_end, max_work_end) : int(line[8]);
//				// Current location
//				current_location<-line[10] = "nil" ? any_location_in(living_place) : point(float(line[10]), float(line[11]));
//			}
//		}
		
	}
}

// Species to represent the people using the skill moving
species people skills: [moving]{
	// id
	int id;
	// Objective (resting or working)
	string objective <- "resting";
	// Working parameters
	int start_work;
	int end_work;
	// Curent location
	point location;
	// Working and living place
	road living_place;
	road working_place;
	// Target point of the agent
	point target;
	// Speed of the agent
	float speed <- (5 + rnd(30)) #km/#h;
	// Currante state (susceptible = 0, infected = 1 or recovered = 2)
	int state <- 0;
	
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
		do goto (target: target, on: road, recompute_path: false, return_path: false);
		
		if (location = target) {
			target <- nil;
		}	
	}
	
	// Reflex to change the state of the agent to infected
	reflex change_to_infected_state when: state = 0 {
		float proba <- 1 - (1 - mosquitoes_daily_rate_of_bites * mosquitoes_susceptibility_to_dengue);
		ask mosquitoes at_distance(20 #m) {
			// Check the mosquitoes state
			if state = 2 and flip(proba){
				myself.state <- 1;
				break;
			}
		}
	}
	
	// Reflex to change the state of the agent to recovered
	reflex change_to_recovered_state when: state = 1 and flip(poeple_daily_recovery_rate) {
		state <- 2;
	}
	
	aspect default {
		if state = 0 {
			draw circle(20) color: #yellow;	
		} else if state = 1 {
			draw circle(20) color: #blue;
		} else {
			draw circle(20) color: #green;
		}	
	}
}

// Species to represent the mosquitoes using the skill moving
species mosquitoes skills: [moving] {
	// Id
	int id;
	// Default speed of the agent
	float speed <- (5 + rnd(10)) #km / #h;
	// State of the agent (susceptible = 0, exposed = 1 or infected = 2)
	int state <- 0;
	// The initial point of the agent
	point starting_point;
	// Mooving radius
	float max_move_radius <- 200.0 #m;
	// Prabability of move
	float move_probability <- 0.5;
	// Target
	point target;
	// Mooving bounds
	geometry bounds;

	// Reflex to stay in current location or select a random destination
	reflex stay	when: (target = nil) and (flip(move_probability)) {
		target <- any_location_in(bounds);
	}
	
	// Reflex to move
	reflex move when: target != nil {
		do goto (target: target, on: road, recompute_path: false, return_path: false);
		
		if target = location {
			target <- nil;
		}
	}
	
	// Reflex to change the state of the agent to exposed
	reflex change_to_exposed_state when: state = 0 {
		float proba <- 1 - (1 - mosquitoes_daily_rate_of_bites * mosquitoes_susceptibility_to_dengue);
		ask people at_distance(20 #m) {
			// Check the people state
			if state = 1 and flip(proba){
				myself.state <- 1;
			}
		}
	}
	
	// Reflex to change the state of the agent to infected
	reflex change_to_infected_state when: state = 1 and flip(mosquitoes_daily_latency_rate) {
		state <- 2;
	}
	
	// Reflex to generate a new offspring
	reflex oviposition when: flip(mosquitoes_oviposition_rate){
		outbreaks selected_outbreak <- outbreaks at_distance(5 #m) closest_to(self);
		selected_outbreak.eggs <- selected_outbreak.eggs + rnd(1, mosquitoes_max_carrying_capacity);
		selected_outbreak.active <- true;

//		TODO: change to generic values
//		ask mosquitoes at_distance(2 #m) {
//			if flip(1) {
//				create mosquitoes number: rnd(1, 5) {
//					starting_point <- myself.location;
//					location <- starting_point;
//					bounds <- circle(200, starting_point);
//				}
//				break;
//			}
//		}
	}
	
	
	aspect default {
		if state = 0 {
			draw circle(10) color: #blue;
		} else if state = 1 {
			draw circle(10) color: #black;
		} else {
			draw circle(10) color: #red;
		}
	}
}

// Species to represent the outbreaks points
species outbreaks {
	// Id
	int id;
	// Osmid
	string osmid;
	// Outbreak center
	point location;
	// This outbreak focus has eggs
	bool active <- false;
	// Number of eggs
	int eggs <- 0;
		
	reflex adult_offspring when: every(12 #hour) and active = true {
		if eggs > 0 {
			int num_new_mosquitoes <- round(eggs_to_mosquitoes * eggs);
			eggs_to_mosquitoes <- eggs_to_mosquitoes - num_new_mosquitoes;
			
			create mosquitoes number: num_new_mosquitoes {
				starting_point <- any_location_in(one_of(road));
				location <- starting_point;
				bounds <- circle(200, myself.location);
				state <- 1;
			}	
		} else {
			active <- false;
		}
	}
	
	reflex aquatic_phase_death when: every(12 #hour) and active = true {
		if eggs > 0 {
			int aquatic_elimination <- round(aquatic_phase_mortality_rate * eggs);
			eggs <- eggs - aquatic_elimination;
		} 
		if eggs <= 0 {
			active <- false;
		}
	}
	
	
		
}

//Species to represent the buildings
species building {
	aspect default {
		draw shape color: #gray;
	}
}

//Species to represent the roads
species road {
	// Osmid
	string osmid;
	aspect default {
		draw shape color: #black;
	} 
}

experiment dengue_propagation type: gui {
	output {
		display city type: opengl{
			species building aspect: default ;
			species road aspect: default ;
			species people aspect: default ;
			species mosquitoes aspect: default ;
		}
	}
}

