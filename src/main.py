from user_cases.simulation import Simulation

if __name__ == "__main__":
    simulation = Simulation(
        "0",
        10,
        5,
        10,
        5,
        2,
        "temp/shp",
        "dengue_propagation",
        1,
    )

    simulation.run()
