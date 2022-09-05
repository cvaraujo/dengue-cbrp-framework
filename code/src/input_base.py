import pandas as pd
import random

class BaseInputSimulation:

    @staticmethod
    def base_mosquitoes_input(output_filename: str, number_of_mosquitoes: int):
        data = {
            "name": ["mosquito" + str(i) for i in range(number_of_mosquitoes)],
            "id": [str(i) for i in range(number_of_mosquitoes)],
            "color_msq": ["#black" for _ in range(number_of_mosquitoes)],
            "speed": ["nil" for _ in range(number_of_mosquitoes)],
            "state_msq": [random.randint(0,1) for _ in range(number_of_mosquitoes)],
            "start_place.osmid": ["nil" for _ in range(number_of_mosquitoes)],
            "start_point.x": ["nil" for _ in range(number_of_mosquitoes)],
            "start_point.y": ["nil" for _ in range(number_of_mosquitoes)],
            "last_position.osmid": ["nil" for _ in range(number_of_mosquitoes)],
            "location.x": ["nil" for _ in range(number_of_mosquitoes)],
            "location.y": ["nil" for _ in range(number_of_mosquitoes)],
        }
        df = pd.DataFrame(data)
        self.write_csv(df, output_filename)

    @staticmethod
    def base_human_input(output_filename: str, number_of_humans: int):
        data = {
            "name": ["human" + str(i) for i in range(number_of_humans)],
            "id": [str(i) for i in range(number_of_humans)],
            "color": ["#yellow" for _ in range(number_of_humans)],
            "speed": ["nil" for _ in range(number_of_humans)],
            "state": [random.randint(0,1) for _ in range(number_of_humans)],
            "living_place.osmid": ["nil" for _ in range(number_of_humans)],
            "working_place.osmid": ["nil" for _ in range(number_of_humans)],
            "start_work": ["nil" for _ in range(number_of_humans)],
            "end_work": ["nil" for _ in range(number_of_humans)],
            "objective": ["resting" for _ in range(number_of_humans)],
            "last_position.osmid": ["nil" for _ in range(number_of_humans)],
            "location.x": ["nil" for _ in range(number_of_humans)],
            "location.y": ["nil" for _ in range(number_of_humans)],
        }
        df = pd.DataFrame(data)
        self.write_csv(df, output_filename)

    @staticmethod
    def base_xml_headless_simulation(
            filename: str,
            dengue_model_filename: str,
            build_filename: str,
            road_filename: str,
            shape_filename: str,
            mosquitoes_filename: str,
            people_filename: str,
            mosquitoes_output: str,
            people_output: str,
    ):
        xml_file = open(filename, 'w')
        xml_file.write("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>")
        xml_file.write("<Experiment_plan>")
        xml_file.write("<Simulation id=\"1\" sourcePath=\"" + dengue_model_filename + "\" finalStep=\"2\" experiment=\"explore_model\">")
        xml_file.write("<Parameters>\n")
        xml_file.write("<Parameter var=\"build_filename\" type=\"STRING\" value=\"" + build_filename + "\" />\n")
        xml_file.write("<Parameter var=\"road_filename\" type=\"STRING\" value=\"" + road_filename + "\" />\n")
        xml_file.write("<Parameter var=\"shape_filename\" type=\"STRING\" value=\"" + shape_filename + "\" />\n")
        xml_file.write("<Parameter var=\"mosquitoes_data_filename_inp\" type=\"STRING\" value=\"" + mosquitoes_filename + "\" />\n")
        xml_file.write("<Parameter var=\"human_data_filename_inp\" type=\"STRING\" value=\"" + people_filename + "\" />\n")
        xml_file.write("<Parameter var=\"mosquitoes_data_filename_otp\" type=\"STRING\" value=\"" + mosquitoes_output + "\" />\n")
        xml_file.write("<Parameter var=\"human_data_filename_otp\" type=\"STRING\" value=\"" + people_output + "\" />\n")
        xml_file.write("</Parameters>\n")
        xml_file.write("</Simulation>\n")
        xml_file.write("</Experiment_plan>\n")

        xml_file.close()

    @staticmethod
    def write_csv(self, df: pd.DataFrame, filename: str):
        df.to_csv(filename)

