from typing import Dict, List, Tuple, Set, Optional
import osmnx as ox
from domain.node import *
from domain.arc import *

class Graph:
    def __init__(self):
        self.n: int = 0
        self.m: int = 0
        self.b: int = 0
        self.key_arc_map: Dict[int, Arc] = {}
        self.osmid_node_map: Dict[str, Node] = {}
        self.block_nodes: Dict[int, List[int]] = {}
        self.block_pairs: Dict[int, List[Tuple[int, int]]] = {}
        self.block_arcs: Dict[int, List[Arc]] = {}
        self.nodes: Dict[int, Node] = {}
        self.arcs: Dict[int, List[Arc]] = {}
        self.plot: bool = False

    def add_osm_node(self, node: Node):
        self.n += 1
        self.nodes[node.index] = node
        self.osmid_node_map[node.osmid] = node

    def add_osm_arc(self, arc_tuple: Tuple[int, int, dict], with_two_ways: bool = True) -> bool:
        source_id, target_id, arc_data = arc_tuple
        source = self.osmid_node_map[str(source_id)]
        target = self.osmid_node_map[str(target_id)]

        if source.index == target.index or target.index in [a.target.index for a in self.arcs[source.index]]:
            return False

        name = str(arc_data.get("name", ""))
        oneway = arc_data.get("oneway", False) if not with_two_ways else False
        osmid = str(arc_data.get("osmid", ""))
        length = arc_data.get("length", 0.0)
        id_key = arc_data.get("id_key", -1)

        new_arc = Arc(osmid, oneway, name, length, source, target, id_key)
        self.arcs[source.index].append(new_arc)
        self.key_arc_map[id_key] = new_arc
        self.m += 1

        if with_two_ways:
            rev_key = id_key + 1 if id_key != -1 else -1
            rev_arc = Arc(osmid, False, name, length, target, source, rev_key)
            self.arcs[target.index].append(rev_arc)
            self.key_arc_map[rev_key] = rev_arc
            self.m += 1

        return True

    def get_arc_block_from_osmid_nodes(self, source: str, target: str) -> int:
        source_node = self.osmid_node_map[source]
        target_node = self.osmid_node_map[target]

        for arc in self.arcs[source_node.index]:
            if arc.target.index == target_node.index:
                return arc.block
        return -1

    def get_arc_index(self, source: int, target: int) -> int:
        if source >= len(self.arcs):
            return -1
        
        for i, arc in enumerate(self.arcs[source]):
            if arc.target.index == target:
                return i
        return -1

    def get_arc(self, source: int, target: int) -> Optional[Arc]:
        for arc in self.arcs.get(source, []):
            if arc.target.index == target:
                return arc
        return None

    # N1, N4, 
    def print_graph(self):
        print("Number of nodes: ", self.n)
        print("Number of arcs: ", self.m)
        print("Number of blocks: ", self.b)

        for i in range(self.n):
            print(f"Node {i}: {self.nodes[i].index} = {self.nodes[i].get_blocks()}")

        for i in range(self.n):
            for j in range(len(self.arcs[i])):
                print(f"Arc {i} -> {self.arcs[i][j].target.index}: {self.arcs[i][j].block} = {self.arcs[i][j].length}")

    def plot_graph(self, osm):
        g = osm.osm_map
        colors = ["r", "g", "b", "c"]
        route = []

        for b in range(1, self.b + 1):
            dirgrassa = []
            for i, j in self.block_pairs.get(b, []):
                dirgrassa.append((i, j))
                route.append([int(self.nodes[i].osmid), int(self.nodes[j].osmid)])
            print(dirgrassa)

        try:
            ox.plot.plot_graph_routes(
                g,
                route,
                route_colors=[colors[(i % len(colors))] for i in range(len(route))],
                save=False,
            )
        except Exception as e:
            print(e)
