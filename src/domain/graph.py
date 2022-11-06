import osmnx as ox
import networkx as nx
from domain.arc import Arc
from domain.node import Node
from domain.utils import *
from typing import List, Dict
import logging
from time import sleep


class Graph:
    def __init__(self, osmnx_graph=None, plot=False):
        self._nodes = []
        self._arcs = []
        self._osmnx_graph = osmnx_graph
        self._n = 0
        self._m = 0
        self._b = 0
        self._key_arc_map = dict()
        self._osmid_node_map = dict()
        self._block_nodes = dict()
        self._block_arcs = dict()
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

    def set_edge_blocks(self):
        used_arcs = dict()
        n = self._n

        # Complete the graph
        arcs_ = [[] for _ in range(n)]
        for i in range(n):
            for arc in self._arcs[i]:
                # Copy
                arcs_[i].append(arc)
                if arc.oneway:
                    rev_arc = copy(arc)
                    rev_arc.source, rev_arc.target = arc.target, arc.source
                    arcs_[arc.target].append(rev_arc)

        # Fill the used arcs with False
        for i in range(n):
            for j in self._arcs[i]:
                used_arcs[(i, j.target)] = False

        # compute the set of cicles
        valid_faces = Utils.compute_faces(self._nodes, arcs_)
        invalid_faces = []

        # Get the valid face arcs
        self._b = 0
        for face in valid_faces:
            face_arcs = [
                (face[i - 1], face[i])
                for i in range(1, len(face))
                if (face[i - 1], face[i]) in used_arcs
            ]
            if (face[-1], face[0]) in used_arcs:
                face_arcs.append((face[-1], face[0]))

            if len(face_arcs) == len(face):
                self._block_nodes[self._b] = face_arcs
                self._b += 1
                for arc in face_arcs:
                    used_arcs[arc] = True
            else:
                invalid_faces.append(face)

        # Invalid faces
        invalid_faces = sorted(invalid_faces, key=lambda x: len(x), reverse=True)
        for face in invalid_faces:
            face_arcs = Utils.get_cycle(n, face, self._arcs, used_arcs)
            if len(face_arcs) > 0:
                self._block_nodes[self._b] = face_arcs
                self._b += 1
                for arc in face_arcs:
                    used_arcs[arc] = True

        # set the blocks
        for key in self._block_nodes.keys():
            for pair in self._block_nodes[key]:
                i, j = pair[0], pair[1]
                self._nodes[i].add_block(key)
                self._nodes[j].add_block(key)
                self._arcs[i][self.get_edge(i, j)].block = key

    def get_edge(self, i: int, j: int) -> int:
        for k in range(len(self._arcs[i])):
            if self._arcs[i][k].target == j:
                return k
        return None

    def get_edge_by_key(self, key: int):
        # If the key has already been searched
        if key in self._key_arc_map:
            return self._key_arc_map[key]

        # New key
        for arc in self_arcs:
            if arc.key == key:
                self._key_arc_map[key] = arc
                return arc

    def plot_graph(self):
        graph = self._osmnx_graph.osm_map
        colors = ["r", "g", "b", "c"]
        n_route = []
        route = []

        for block in self._block_nodes.keys():
            # route = []
            print(self._block_nodes[block])
            for arc in self._block_nodes[block]:
                route.append([self._nodes[arc[0]].osmid, self._nodes[arc[1]].osmid])

        if len(route) > 0:
            try:
                ox.plot.plot_graph_routes(
                    graph,
                    route,
                    route_colors=[colors[i % len(colors)] for i in range(len(route))],
                    save=True,
                    filepath="faces.png",
                )
                n_route += route
            except Exception as e:
                print(e)

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
