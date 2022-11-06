from domain.osm import OpenStreetMap
from domain.graph import Graph
from domain.arc import Arc
from domain.node import Node
import osmnx as ox
import logging, os
from pathlib import Path


class MapAdapter:
    @staticmethod
    def convert_osm_to_graph(osm: OpenStreetMap, path="") -> Graph:
        try:
            # Get the OSMnx map
            osm_map = osm.osm_map

            # Get nodes and edges
            nodes = osm_map.nodes.data()
            edges = osm_map.edges.data()

            # Create graph object
            graph = Graph(osmnx_graph=osm)

            # Add nodes to graph
            i = 0
            for node in nodes:
                graph.add_osm_node(Node(node[0], i, node[1]["y"], node[1]["x"]))
                i += 1

            # Add arcs to the graph
            graph.arcs = [[] for _ in range(graph.n)]

            for edge in edges:
                graph.add_osm_arc(edge)

            graph.set_edge_blocks()

            return graph
        except Exception as ex:
            logging.info("[!] Error to convert the OSM map to Graph.")
            return None

    @staticmethod
    def export_osm_to_shapefile(osm: OpenStreetMap, path: str) -> bool:
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            ox.io.save_graph_shapefile(osm.osm_map, filepath=path, directed=True)
            return True
        except:
            logging.info("[!] Error to save the shapefiles.")
            return None

    @staticmethod
    def write_graph_to_txt(graph: Graph, path: str):
        try:
            graph_file = open(path, "w")

            n = graph.n
            graph_file.write(str(n) + " " + str(graph.m) + " " + str(graph.b) + "\n")

            for node in graph.nodes:
                graph_file.write(
                    "N "
                    + str(node.index)
                    + " "
                    + str(node.lat)
                    + " "
                    + str(node.lon)
                    + " "
                    + ",".join([str(b) for b in node.block])
                    + "\n"
                )

            for i in range(n):
                for arc in graph.arcs[i]:
                    graph_file.write(
                        "A "
                        + str(i)
                        + " "
                        + str(arc.target)
                        + " "
                        + "{:.2f}".format(arc.length)
                        + " "
                        + str(arc.block)
                        + " "
                        + str(arc.cases)
                        + " "
                        + str(arc.osmid)
                        + "\n"
                    )
            graph_file.close()
        except:
            logging.info("[!] Error to convert the OSM map to Graph.")
            return None
