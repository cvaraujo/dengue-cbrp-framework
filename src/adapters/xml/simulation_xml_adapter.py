import os


class XmlSimulationAdapter:
    @staticmethod
    def create_xml_headless_simulation(
        filename: str,
        head: dict,
        parameters: dict,
    ):
        xml_file = open(filename, "w")

        # Basic simulation parameters
        id = head["id"] if "id" in head else 0
        final_step = head["final_step"] if "final_step" in head else "2"
        model = head["model"]
        experiment = (
            head["experiment"]
            if "experiment" in head
            else "headless-dengue-propagation"
        )

        # Head of the xml
        xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n <Experiment_plan>\n <Simulation id="'
            + str(id)
            + '" sourcePath="'
            + model
            + '" finalStep="'
            + str(final_step)
            + '" experiment="'
            + experiment
            + '">\n'
        )

        # Parameters
        xml += "<Parameters>\n"
        for param in parameters.keys():
            type_param, value = parameters[param]
            xml += (
                '<Parameter var="'
                + param
                + '" type="'
                + type_param
                + '" value="'
                + str(value)
                + '"/>\n'
            )
        # foot
        xml += "</Parameters>\n" + "</Simulation>\n" + "</Experiment_plan>\n"

        xml_file.write(xml)
        xml_file.close()
