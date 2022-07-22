from input_base import BaseInputSimulation


if __name__ == '__main__':
    # Create a new xml file
    BaseInputSimulation.base_xml_headless_simulation(
        "gama-default.xml",
        "model.gama",
        "build.shp",
        "road.shp",
        "shape.shp",
        "mosquitoes.csv",
        "people.csv",
        "mosquitoes_1.csv",
        "people_1.csv"
    )
