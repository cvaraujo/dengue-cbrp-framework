from typing import Dict, List, Tuple, Optional
import copy
from venv import logger
from domain.node import *
from domain.arc import *
from domain.utils import compute_faces


class Graph:
    def __init__(self):
        self.n: int = 0
        self.m: int = 0
        self.b: int = 0
        self.key_arc_map: Dict[int, Arc] = {}
        self.osmid_node_map: Dict[str, Node] = {}
        self.block_nodes: Dict[int, List[int]] = {}
        self.block_pairs: Dict[int, List[Tuple[int, int]]] = {}
        self._block_arcs: Dict[int, List[Arc]] = {}
        self.nodes: Dict[int, Node] = {}
        self.arcs: Dict[int, List[Arc]] = {}
        self.plot: bool = False

    @property
    def block_arcs(self):
        return self._block_arcs

    @block_arcs.setter
    def block_arcs(self, value):
        self._block_arcs = value

    def add_osm_node(self, node: Node):
        self.n += 1
        self.nodes[node.index] = node
        self.osmid_node_map[node.osmid] = node

    def add_osm_arc(
        self, arc_tuple: Tuple[int, int, dict], with_two_ways: bool = True
    ) -> bool:
        source_id, target_id, arc_data = arc_tuple
        source = self.osmid_node_map[str(source_id)]
        target = self.osmid_node_map[str(target_id)]

        if source.index == target.index or target.index in [
            a.target.index for a in self.arcs[source.index]
        ]:
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

    def print_graph(self):
        print("Number of nodes: ", self.n)
        print("Number of arcs: ", self.m)
        print("Number of blocks: ", self.b)

        for i in range(self.n):
            print(f"Node {i}: {self.nodes[i].index} = {self.nodes[i].get_blocks()}")

        for i in range(self.n):
            for j in range(len(self.arcs[i])):
                print(
                    f"Arc {i} -> {self.arcs[i][j].target.index}: {self.arcs[i][j].block} = {self.arcs[i][j].length}"
                )

    def set_graph_blocks(self):
        used_arcs = {
            (i, arc.target.index): False for i in range(self.n) for arc in self.arcs[i]
        }
        graph_prime = copy.deepcopy(self)

        # Copy arcs with both directions
        for i in range(self.n):
            for arc in self.arcs[i]:
                if arc.oneway:
                    rev_arc = copy.deepcopy(arc)
                    rev_arc.source, rev_arc.target = arc.target, arc.source
                    graph_prime.arcs[rev_arc.source.index].append(rev_arc)

        # Remove dead ends
        i = 0
        while i < self.n:
            if len(graph_prime.arcs[i]) == 1:
                graph_prime.arcs[i] = []
                for j in range(self.n):
                    if j == i:
                        continue
                    k = 0
                    while k < len(graph_prime.arcs[j]):
                        if graph_prime.arcs[j][k].target.index == i:
                            del graph_prime.arcs[j][k]
                            break
                        k += 1
                i = 0
            i += 1

        valid_faces = compute_faces(graph_prime)
        invalid_faces = []

        for face in valid_faces:
            face_arcs = [
                (face[i - 1], face[i])
                for i in range(1, len(face))
                if (face[i - 1], face[i]) in used_arcs
                and not used_arcs[(face[i - 1], face[i])]
            ]
            if (face[-1], face[0]) in used_arcs and not used_arcs[(face[-1], face[0])]:
                face_arcs.append((face[-1], face[0]))

            if len(face_arcs) == len(face):
                self.block_pairs[self.b] = face_arcs
                self.block_nodes[self.b] = face
                for arc in face_arcs:
                    used_arcs[arc] = True
                self.b += 1
            else:
                invalid_faces.append(face)

        for key in range(self.b):
            self.block_arcs[key] = []
            for i, j in self.block_pairs[key]:
                k = self.get_arc_index(i, j)
                self.nodes[i].add_block(key)
                self.nodes[j].add_block(key)
                self.arcs[i][k].block = key
                self.block_arcs[key].append(self.arcs[i][k])

        logger.info(
            f"[*] Graph has {self.n} nodes, {self.m} arcs and {self.b} blocks..."
        )
