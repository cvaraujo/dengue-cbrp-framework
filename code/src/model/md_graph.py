import osmnx as ox
import networkx as nx
from model.md_arc import Arc
from model.md_node import Node
from model.md_utils import *


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

    def __str__(self):
        return str(self._n) + " nodes and " + str(self._m) + " arcs"

    def create_graph_from_addr(self, address, radius):
        try:
            self._osmnx_graph = ox.graph_from_address(
                address, dist=radius, simplify=True
            )

            ox.plot_graph(self._osmnx_graph)

            # Get nodes and edges
            nodes = self._osmnx_graph.nodes.data()
            arcs = self._osmnx_graph.edges.data()

            # Create the set of nodes
            for node in nodes:
                new_node = Node(node[0], self._n, node[1]["y"], node[1]["x"])
                self._nodes.append(new_node)
                self._osmid_node_map[node[0]] = new_node
                self._n += 1

            # Create the set of arcs
            self._arcs = [[] for _ in range(self._n)]

            for arc in arcs:
                source = self._osmid_node_map[arc[0]].index
                target = self._osmid_node_map[arc[1]].index
                arc_dict = arc[2]

                # Ignore self loop
                if source == target:
                    continue

                # Treating empty parameters
                name = arc_dict["name"] if "name" in arc_dict else ""
                oneway = arc_dict["oneway"] if "oneway" in arc_dict else False
                osmid = arc_dict["osmid"] if "osmid" in arc_dict else ""
                length = arc_dict["length"] if "length" in arc_dict else 0.0

                # Create a new arc
                new_arc = Arc(
                    osmid,
                    oneway,
                    name,
                    length,
                    source,
                    target,
                    self._m,
                )

                # Add new arc and map the id
                self._arcs[source].append(new_arc)
                self._key_arc_map[self._m] = new_arc
                self._m += 1
        except Exception as ex:
            print(ex)

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
            found = False
            oriented_block = []
            ch_nodes = [node.index for node in S]

            while start_point < len(S) - 2 and not found:
                u_ = S[start_point]
                for v in self._arcs[u_.index]:
                    if v.target in ch_nodes:
                        v_ = self._nodes[v.target]
                        for k in self._arcs[v.target]:
                            if k.target != u_.index and k.target in ch_nodes:
                                k_ = self._nodes[k.target]
                                # Compute the determinant
                                det = (v_.lon - u_.lon) * (k_.lat - u_.lat) - (
                                    k_.lon - u_.lon
                                ) * (v_.lat - u_.lat)

                                temp_block = []

                                if det < 0:
                                    temp_block = Utils.get_directed_block(
                                        u_.index,
                                        v_.index,
                                        k_.index,
                                        cycles[key],
                                        n,
                                        self._arcs,
                                        used_arcs,
                                    )
                                else:
                                    temp_block = Utils.get_directed_block(
                                        k_.index,
                                        v_.index,
                                        u_.index,
                                        cycles[key],
                                        n,
                                        self._arcs,
                                        used_arcs,
                                    )

                                if len(temp_block) > 0:
                                    self._block_nodes[self._b] = temp_block
                                    self._b += 1
                                    for arc_pair in temp_block:
                                        used_arcs[(arc_pair[0], arc_pair[1])] = True
                                    found = True
                                    break
                    if found:
                        break
                start_point += 1

        # set the blocks
        for key in self._block_nodes.keys():
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
