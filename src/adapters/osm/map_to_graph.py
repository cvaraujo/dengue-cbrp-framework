from domain.osm import OpenStreetMap
from domain.graph import Graph
from domain.arc import Arc
from domain.node import Node
import logging, os


class MapToGraph:
    @staticmethod
    def convert_osm_to_graph(osm: OpenStreetMap) -> Graph:
        try:
            # Get the OSMnx map
            osm_map = osm.osm_map

            # Get nodes and edges
            nodes = osm_map.nodes.data()
            edges = osm_map.edges.data()

            # Create graph object
            graph = Graph()

            # Add nodes to graph
            i = 0
            for node in nodes:
                graph.add_osm_node(Node(node[0], i, node[1]["y"], node[1]["x"]))
                i += 1

            # Add arcs to the graph
            graph.arcs = [[] for _ in range(graph.n)]

            for edge in edges:
                graph.add_osm_arc(edge)

            return graph
        except Exception as ex:
            print(ex)
            logging.info("[!] Error to convert the OSM map to Graph.")
            return None
