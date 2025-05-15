import os
from typing import List
import pandas as pd
from adapters.sql.postgree import PostgreSQLAdapter
from domain.graph import Graph
from adapters.sql import *
import domain.utils as Utils

class DeterministicInstance:
    def __init__(self, graph: Graph):
        self._graph = graph
        self._sql = PostgreSQLAdapter()

    def get_infected_per_block(self, df: pd.DataFrame, coord_blocks: List) -> List:
        filtered_df: pd.DataFrame = df.query("classification != 5")
        infected_per_block = [0] * self._graph.b

        for _, row in filtered_df.iterrows():
            y, x = float(row["y"]), float(row["x"])
            for i, polygon in enumerate(coord_blocks):
                if Utils.point_in_polygon((y, x), polygon):
                    infected_per_block[i] += 1
                    break

        return infected_per_block
    
    def write_instance(self, filename: str, infected_per_block):
        with open(filename, "w") as file:
            # Header
            file.write(f"{self._graph.n} {self._graph.m} {self._graph.b}\n")

            # Nodes
            for id, node in self._graph.nodes.items():
                blocks = ",".join(str(b) for b in node.get_blocks())
                file.write(f"N {id} {node.lat:.6f} {node.lon:.6f} {blocks}\n")

            # Arcs
            for idx in range(self._graph.n):
                for arc in self._graph.arcs[idx]:
                    block = -1 if arc.block == -1 else arc.block
                    file.write(f"A {arc.source.index} {arc.target.index} {arc.length:.3f} {block}\n")

            # Infected per block
            for i, infected in enumerate(infected_per_block):
                if infected > 0:
                    file.write(f"B {i} {infected}\n")

    def generate_deterministic_instance(self, city: str, map_size: int, start_date: str, end_date: str, output_folder: str, id: int) -> bool:
        print("[*] Getting Real Cases...")
        location = "ALTO SANTO" if city == "Alto Santo, Ceará, Brasil" else "LIMOEIRO"
        cases = self._sql.get_notifications_between_dates(start_date, end_date, location)

        print("[*] Getting all blocks as polygons...")
        coord_blocks = Utils.all_blocks_as_polygon(self._graph)

        print("[*] Mapping notifications to street-blocks...")
        infected_per_block = self.get_infected_per_block(cases, coord_blocks)

        print(f"\t[*] There are {sum(infected_per_block)} notifications mapped between {start_date} and {end_date}...")

        if sum(infected_per_block) < 5:
            return False

        print("[*] Writing instance...")
        instance_name = os.path.join(
            output_folder,
            f"{'alto-santo' if city == 'Alto Santo, Ceará, Brasil' else 'limoeiro'}-{map_size}-{id}.txt"
        )
        self.write_instance(instance_name, infected_per_block)

        print("[*] Done!")
        return True
