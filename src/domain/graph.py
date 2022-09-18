import osmnx as ox
import networkx as nx
from domain.arc import Arc
from domain.node import Node
from domain.utils import *
from typing import List, Dict
import logging


class Graph:
    def __init__(self, plot=False):
        self._nodes = []
        self._arcs = []
        self._osmnx_graph = None
        self._n = 0
        self._m = 0
        self._b = 0
        self._key_arc_map = dict()
        self._osmid_node_map = dict()
        self._block_nodes = dict()
        self.plot = plot

    def add_osm_node(self, node: Node):
        self._nodes.append(node)
        self._osmid_node_map[node.osmid] = node
        self._n += 1

    def add_osm_arc(self, arc: List):
        source = self._osmid_node_map[arc[0]].index
        target = self._osmid_node_map[arc[1]].index
        arc_dict = arc[2]

        # Ignore self loop
        if source == target:
            return

        # Treating empty parameters
        name = arc_dict["name"] if "name" in arc_dict else ""
        oneway = arc_dict["oneway"] if "oneway" in arc_dict else False
        osmid = arc_dict["osmid"] if "osmid" in arc_dict else ""
        length = arc_dict["length"] if "length" in arc_dict else 0.0
        id_key = arc_dict["id_key"] if "id_key" in arc_dict else -1

        # Create a new arc
        new_arc = Arc(
            osmid,
            oneway,
            name,
            length,
            source,
            target,
            id_key,
        )

        # Add new arc and map the id
        self._arcs[source].append(new_arc)
        self._key_arc_map[self._m] = new_arc
        self._m += 1

    def _get_sequence(
        self, start_point: int, S: List, ch_nodes: List, cycles: List, used_arcs: Dict
    ):
        nodes = self._nodes
        u_ = S[start_point]

        # Get the adjacent points in convex hull
        adj_u = [v.target for v in self._arcs[u_.index] if v.target in ch_nodes]

        # Get the third node
        for v in adj_u:
            v_ = self._nodes[v]
            adj_v = [
                k.target
                for k in self._arcs[v]
                if (k.target in ch_nodes) and (k.target != u_.index)
            ]

            #
            for k in adj_v:
                k_ = self._nodes[k]
                # Compute the determinant
                det = (v_.lon - u_.lon) * (k_.lat - u_.lat) - (k_.lon - u_.lon) * (
                    v_.lat - u_.lat
                )

                # Return the clockwise order
                if det < 0:
                    temp_block = Utils.get_directed_block(
                        u_.index,
                        v_.index,
                        k_.index,
                        cycles,
                        self._n,
                        self._arcs,
                        used_arcs,
                    )
                else:
                    temp_block = Utils.get_directed_block(
                        k_.index,
                        v_.index,
                        u_.index,
                        cycles,
                        self._n,
                        self._arcs,
                        used_arcs,
                    )

                if len(temp_block) > 0:
                    return temp_block
        return None

    def create_blocks(self):
        used_arcs = dict()
        n = self._n

        # Fill the used arcs with False
        for i in range(n):
            for j in self._arcs[i]:
                used_arcs[(i, j.target)] = False

        # compute the set of cicles
        cycles = Utils.compute_faces(self._nodes, self._arcs)

        for key in cycles.keys():
            # Compute the CH
            S = Utils.get_convex_hull(key, self._nodes, cycles)

            # Ignoring cycles of size 2
            if len(S) <= 2:
                continue

            start_point = 0
            oriented_block = []
            ch_nodes = [node.index for node in S]

            while start_point < len(S) - 2:
                new_block = self._get_sequence(
                    start_point, S, ch_nodes, cycles[key], used_arcs
                )
                # Valid face
                if new_block is not None:
                    self._block_nodes[self._b] = new_block
                    self._b += 1
                    for arc_pair in new_block:
                        used_arcs[(arc_pair[0], arc_pair[1])] = True
                    break
                start_point += 1

        # set the blocks
        for key in self._block_nodes.keys():
            print(self._block_nodes[key])
            for pair in self._block_nodes[key]:
                i, j = pair[0], pair[1]
                self._nodes[i].add_block(key)
                self._nodes[j].add_block(key)
                self._arcs[i][self.get_edge(i, j)].block = key

    def get_edge(self, i, j):
        for k in range(len(self._arcs[i])):
            if self._arcs[i][k].target == j:
                return k
        return -1

    def get_edge_by_key(self, key: int):
        pass

    @property
    def nodes(self):
        return self._nodes

    @nodes.setter
    def nodes(self, value):
        self._nodes = value

    @property
    def arcs(self):
        return self._arcs

    @arcs.setter
    def arcs(self, value):
        self._arcs = value

    @property
    def n(self):
        return self._n

    @n.setter
    def n(self, value):
        self._n = value

    @property
    def m(self):
        return self._m

    @m.setter
    def m(self, value):
        self._m = value

    @property
    def b(self):
        return self._b

    @b.setter
    def b(self, value):
        self._b = value
