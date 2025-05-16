import os, copy
import osmnx as ox
import geopandas as gpd
from domain.osm import *
from domain.graph import *
from domain.utils import *

class MapAdapter:
    @staticmethod
    def add_key_block_arc_attrs(osm: OpenStreetMap, graph: Graph):
        try:
            for u, v, data in osm.osm_map.edges(data=True):
                data["block"] = graph.get_arc_block_from_osmid_nodes(str(u), str(v))
        except Exception as e:
            print("[!!!] Error:", e)

    @staticmethod
    def export_osm_to_shapefile(osm: OpenStreetMap, graph: Graph, path: str) -> bool:
        try:
            os.makedirs(path, exist_ok=True)
            MapAdapter.add_key_block_arc_attrs(osm, graph)
            gdf_nodes, gdf_arcs = ox.convert.graph_to_gdfs(osm.osm_map)
            gdf_nodes.to_file(path + "/nodes.shp", driver='ESRI Shapefile', encoding='utf-8')
            gdf_arcs.to_file(path + "/edges.shp", driver='ESRI Shapefile', encoding='utf-8')
            return True
        except Exception as e:
            print("[!!!] Error to write the shapefiles:", e)
            return False

    @staticmethod
    def set_graph_blocks(graph: Graph):
        used_arcs = {(i, arc.target.index): False for i in range(graph.n) for arc in graph.arcs[i]}
        graph_prime = copy.deepcopy(graph)

        for i in range(graph.n):
            for arc in graph.arcs[i]:
                if arc.oneway:
                    rev_arc = copy.deepcopy(arc)
                    rev_arc.source, rev_arc.target = arc.target, arc.source
                    graph_prime.arcs[rev_arc.source.index].append(rev_arc)

        # Remove dead ends
        i = 0
        while i < graph.n:
            if len(graph_prime.arcs[i]) == 1:
                graph_prime.arcs[i] = []
                for j in range(graph.n):
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
            face_arcs = [(face[i-1], face[i]) for i in range(1, len(face))
                        if (face[i-1], face[i]) in used_arcs and not used_arcs[(face[i-1], face[i])]]
            if (face[-1], face[0]) in used_arcs and not used_arcs[(face[-1], face[0])]:
                face_arcs.append((face[-1], face[0]))

            if len(face_arcs) == len(face):
                graph.block_pairs[graph.b] = face_arcs
                graph.block_nodes[graph.b] = face
                for arc in face_arcs:
                    used_arcs[arc] = True
                graph.b += 1
            else:
                invalid_faces.append(face)

        for key in range(graph.b):
            graph.block_arcs[key] = []
            for i, j in graph.block_pairs[key]:
                k = graph.get_arc_index(i, j)
                graph.nodes[i].add_block(key)
                graph.nodes[j].add_block(key)
                graph.arcs[i][k].block = key
                graph.block_arcs[key].append(graph.arcs[i][k])

        print("N:", graph.n, ", A:", graph.m, ", B:", graph.b)

    @staticmethod
    def convert_osm_to_graph(osm: OpenStreetMap, always_two_ways: bool) -> Graph:
        osm_map = osm.osm_map
        nodes = list(osm_map.nodes(data=True))
        arcs = list(osm_map.edges(data=True))
        
        graph = Graph()

        for i, (node_id, data) in enumerate(nodes, 0):
            new_node = Node(osmid=str(node_id), index=i, lat=data['y'], lon=data['x'])
            graph.add_osm_node(new_node)

        graph.arcs = [[] for _ in range(graph.n)]
        arc_key = 0
        new_arcs = []

        if always_two_ways:
            for u, v, data in arcs:
                data["id_key"] = arc_key
                if graph.add_osm_arc((u, v, data), with_two_ways=True):
                    new_data = copy.deepcopy(data)
                    new_data["id_key"] = arc_key + 1
                    new_arcs.append((u, v, data))
                    new_arcs.append((v, u, new_data))
                    arc_key += 2
            osm.osm_map.remove_edges_from(list(osm_map.edges()))
            osm.osm_map.add_edges_from(new_arcs)
        else:
            for arc in arcs:
                graph.add_osm_arc(arc, graph)

        MapAdapter.set_graph_blocks(graph)
        return graph